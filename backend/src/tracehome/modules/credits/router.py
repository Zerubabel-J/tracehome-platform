import uuid
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tracehome.auth import require_advertiser, require_seeker
from tracehome.db import get_session
from tracehome.modules.accounts.models import User
from tracehome.modules.credits.models import Lead, Unlock
from tracehome.modules.credits.service import UnlockError, unlock_contact
from tracehome.modules.listings.models import Listing

router = APIRouter(prefix="/api", tags=["credits"])


class ContactOut(BaseModel):
    advertiser_name: str
    phone: str
    email: str


class UnlockOut(BaseModel):
    unlock_id: int
    listing_id: int
    outcome: str
    charged: bool
    balance: int
    contact: ContactOut


class UnlockedListing(BaseModel):
    listing_id: int
    title: str
    unlocked_at: datetime


class LeadOut(BaseModel):
    id: int
    listing_id: int
    listing_title: str
    seeker_name: str
    created_at: datetime


@router.post("/listings/{listing_id}/unlock", response_model=UnlockOut)
def unlock(
    listing_id: int,
    # The browser creates one ID per unlock attempt and sends it again on a retry.
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    user: User = Depends(require_seeker),
    session: Session = Depends(get_session),
):
    try:
        result = unlock_contact(session, user.id, listing_id, idempotency_key)
        session.commit()
    except UnlockError as error:
        session.rollback()  # nothing is spent
        raise HTTPException(error.status, {"code": error.code, "message": error.message})
    except IntegrityError:
        # The database's UNIQUE constraints caught a duplicate that slipped past the checks.
        session.rollback()
        raise HTTPException(409, {"code": "conflict", "message": "Please try again."})
    return asdict(result)


@router.get("/me/unlocks", response_model=list[UnlockedListing])
def my_unlocks(user: User = Depends(require_seeker), session: Session = Depends(get_session)):
    rows = session.execute(
        select(Unlock, Listing.title)
        .join(Listing, Listing.id == Unlock.listing_id)
        .where(Unlock.seeker_id == user.id)
        .order_by(Unlock.created_at.desc())
    ).all()
    return [
        UnlockedListing(listing_id=u.listing_id, title=title, unlocked_at=u.created_at)
        for u, title in rows
    ]


@router.get("/advertiser/leads", response_model=list[LeadOut])
def my_leads(user: User = Depends(require_advertiser), session: Session = Depends(get_session)):
    # Rule: an advertiser never sees another advertiser's private data (invariant 12).
    # The filter uses the advertiser from the database, never an ID sent by the browser.
    rows = session.execute(
        select(Lead, Listing.title, User.display_name)
        .join(Listing, Listing.id == Lead.listing_id)
        .join(User, User.id == Lead.seeker_id)
        .where(Lead.advertiser_id == user.advertiser_id)
        .order_by(Lead.created_at.desc())
        .limit(200)
    ).all()
    return [
        LeadOut(
            id=lead.id,
            listing_id=lead.listing_id,
            listing_title=title,
            seeker_name=seeker_name,
            created_at=lead.created_at,
        )
        for lead, title, seeker_name in rows
    ]
