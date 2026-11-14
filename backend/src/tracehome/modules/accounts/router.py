from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from tracehome.auth import current_user, issue_token
from tracehome.config import get_settings
from tracehome.db import get_session
from tracehome.modules.accounts.models import Advertiser, User
from tracehome.modules.credits.service import usable_balance

router = APIRouter(prefix="/api", tags=["accounts"])


class DemoUser(BaseModel):
    id: int
    display_name: str
    role: str
    advertiser_name: str | None


class DemoUserOption(DemoUser):
    hint: str  # shown in the sign-in menu, worked out live: "seeker, 2 credits"


class Me(DemoUser):
    balance: int | None  # seekers only


class DemoSignIn(BaseModel):
    user_id: int


class SignedIn(BaseModel):
    token: str
    expires_in: int
    user: Me


def _require_demo_enabled() -> None:
    if not get_settings().demo_sign_in_enabled:
        raise HTTPException(404, {"code": "not_found", "message": "Demo sign-in is off."})


def _me(session: Session, user: User) -> Me:
    advertiser = session.get(Advertiser, user.advertiser_id) if user.advertiser_id else None
    return Me(
        id=user.id,
        display_name=user.display_name,
        role=user.role,
        advertiser_name=advertiser.name if advertiser else None,
        balance=usable_balance(session, user.id) if user.role == "seeker" else None,
    )


@router.get("/auth/demo-users", response_model=list[DemoUserOption])
def demo_users(session: Session = Depends(get_session)):
    """The made-up people you can sign in as (decision 82)."""
    _require_demo_enabled()
    rows = session.execute(
        select(User, Advertiser.name)
        .outerjoin(Advertiser, Advertiser.id == User.advertiser_id)
        .where(User.is_active)
        .order_by(User.role.desc(), User.id)
    ).all()
    options = []
    for user, advertiser_name in rows:
        if user.role == "seeker":
            balance = usable_balance(session, user.id)
            hint = f"seeker, {balance} credit{'' if balance == 1 else 's'}"
        else:
            hint = f"advertiser, {advertiser_name}"
        options.append(
            DemoUserOption(
                id=user.id,
                display_name=user.display_name,
                role=user.role,
                advertiser_name=advertiser_name,
                hint=hint,
            )
        )
    return options


@router.post("/auth/demo-sign-in", response_model=SignedIn)
def demo_sign_in(body: DemoSignIn, session: Session = Depends(get_session)):
    _require_demo_enabled()
    user = session.get(User, body.user_id)
    if user is None or not user.is_active:
        raise HTTPException(404, {"code": "not_found", "message": "No such demo user."})
    return SignedIn(
        token=issue_token(user),
        expires_in=get_settings().token_ttl_seconds,
        user=_me(session, user),
    )


@router.get("/me", response_model=Me)
def me(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return _me(session, user)
