"""The moderator console's API: flagged photos waiting for a person (principle 4)."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracehome.auth import require_moderator
from tracehome.db import get_session
from tracehome.modules.accounts.models import Advertiser, User
from tracehome.modules.listings.models import Listing, Photo
from tracehome.modules.review_cases.models import ReviewCase
from tracehome.modules.uploads import storage

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


class ReviewCaseOut(BaseModel):
    id: int
    status: str
    reason: str
    created_at: datetime
    photo_id: int
    listing_id: int
    listing_title: str
    advertiser_name: str
    advertiser_kind: str
    preview_url: str | None  # short-lived link to the held photo; open cases only
    decision: str | None
    decided_by_name: str | None
    decided_at: datetime | None
    note: str | None


class Summary(BaseModel):
    open: int
    approved: int
    rejected: int


class Decision(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(None, max_length=300)


def _cases_query(*conditions):
    decider = select(User.id, User.display_name).subquery()
    return (
        select(ReviewCase, Photo, Listing, Advertiser, decider.c.display_name)
        .join(Photo, Photo.id == ReviewCase.photo_id)
        .join(Listing, Listing.id == Photo.listing_id)
        .join(Advertiser, Advertiser.id == Listing.advertiser_id)
        .outerjoin(decider, decider.c.id == ReviewCase.decided_by)
        .where(*conditions)
    )


def _out(case, photo, listing, advertiser, decided_by_name) -> ReviewCaseOut:
    return ReviewCaseOut(
        id=case.id,
        status=case.status,
        reason=case.reason,
        created_at=case.created_at,
        photo_id=photo.id,
        listing_id=listing.id,
        listing_title=listing.title,
        advertiser_name=advertiser.name,
        advertiser_kind=advertiser.kind,
        # Rule: a held photo is never public. A moderator sees it only through a link the API
        # signs after checking their role, and only while the case is open.
        preview_url=storage.presign_held_photo_view(photo.object_key)
        if case.status == "open"
        else None,
        decision=case.decision,
        decided_by_name=decided_by_name,
        decided_at=case.decided_at,
        note=case.note,
    )


@router.get("/summary", response_model=Summary)
def summary(_: User = Depends(require_moderator), session: Session = Depends(get_session)):
    outcome = func.coalesce(ReviewCase.decision, "open").label("outcome")
    counts = dict(session.execute(select(outcome, func.count()).group_by(outcome)).all())
    return Summary(
        open=counts.get("open", 0),
        approved=counts.get("approved", 0),
        rejected=counts.get("rejected", 0),
    )


@router.get("/cases", response_model=list[ReviewCaseOut])
def list_cases(
    status: Literal["open", "closed"] = Query("open"),
    _: User = Depends(require_moderator),
    session: Session = Depends(get_session),
):
    # Oldest open case first, so nothing waits forever; newest decision first in the history.
    order = ReviewCase.created_at.asc() if status == "open" else ReviewCase.decided_at.desc()
    rows = session.execute(
        _cases_query(ReviewCase.status == status).order_by(order, ReviewCase.id).limit(100)
    ).all()
    return [_out(*row) for row in rows]


@router.post("/cases/{case_id}/decision", response_model=ReviewCaseOut)
def decide(
    case_id: int,
    body: Decision,
    moderator: User = Depends(require_moderator),
    session: Session = Depends(get_session),
):
    # Lock the case, so two moderators clicking at once can't both decide it.
    case = session.scalar(select(ReviewCase).where(ReviewCase.id == case_id).with_for_update())
    if case is None:
        raise HTTPException(404, {"code": "not_found", "message": "No such review case."})
    # Rule: a case is decided once. A second decision is refused, not silently applied.
    if case.status != "open":
        raise HTTPException(
            409, {"code": "already_decided", "message": f"This case was already {case.decision}."}
        )
    photo = session.scalar(select(Photo).where(Photo.id == case.photo_id).with_for_update())

    if body.decision == "approved":
        # Copy the file before committing. If the commit then fails, the case stays open and a
        # retry copies the same file again, which is harmless.
        public_key = "photos/" + photo.object_key.removeprefix("uploads/")
        storage.publish_held_photo(photo.object_key, public_key)
        photo.status = "approved"
        photo.public_key = public_key
    else:
        # Rule: the advertiser is always told why (requirements: "a reason a person can understand").
        photo.status = "rejected"
        photo.reason = body.note or f"Rejected by a moderator: {case.reason}"
    photo.decided_at = func.now()

    case.status = "closed"
    case.decision = body.decision
    case.decided_by = moderator.id
    case.decided_at = func.now()
    case.note = body.note
    session.commit()

    return _out(*session.execute(_cases_query(ReviewCase.id == case_id)).one())
