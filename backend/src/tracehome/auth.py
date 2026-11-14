"""Demo sign-in tokens (decision 82). The target is Amazon Cognito; until then the API signs a
short-lived token for a seeded, made-up user.

The token only says *who* is calling. What they may do is always read from the database on each
request, so deactivating a user takes effect at once, without waiting for the token to expire.
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from tracehome.config import get_settings
from tracehome.db import get_session
from tracehome.modules.accounts.models import User

ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)


def issue_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + timedelta(seconds=settings.token_ttl_seconds),
    }
    return jwt.encode(claims, settings.token_signing_key, algorithm=ALGORITHM)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(401, {"code": "unauthorized", "message": message})


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise _unauthorized("Sign in first.")
    try:
        claims = jwt.decode(
            credentials.credentials, get_settings().token_signing_key, algorithms=[ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Your session expired. Sign in again.")
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid token.")

    user = session.get(User, int(claims["sub"]))
    # Rule: a deactivated user loses access immediately (requirements, invariant 15).
    if user is None or not user.is_active:
        raise _unauthorized("This account is not active.")
    return user


def require_seeker(user: User = Depends(current_user)) -> User:
    if user.role != "seeker":
        raise HTTPException(403, {"code": "forbidden", "message": "Only seekers can do this."})
    return user


def require_advertiser(user: User = Depends(current_user)) -> User:
    if user.role != "advertiser" or user.advertiser_id is None:
        raise HTTPException(403, {"code": "forbidden", "message": "Only advertisers can do this."})
    return user
