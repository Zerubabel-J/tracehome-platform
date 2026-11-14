"""Tests run against a real PostgreSQL 16, because the rules we test (row locks, constraints,
triggers) live in the database. A fresh test database is created and migrated with Alembic, so
the migration itself is tested too."""

import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Point everything at the test database *before* the application reads its settings.
TEST_DB = os.environ.setdefault("TEST_DB_NAME", "tracehome_test")
os.environ["DB_NAME"] = TEST_DB
os.environ["DB_POOL_SIZE"] = "10"  # the parallel tests hold 10 connections at once
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")  # presigning needs keys, never real ones
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("S3_PUBLIC_ENDPOINT_URL", "http://localhost:4566")

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, func, select, text  # noqa: E402

import tracehome.models  # noqa: E402, F401
from tracehome.auth import issue_token  # noqa: E402
from tracehome.config import get_settings  # noqa: E402
from tracehome.db import get_engine, new_session  # noqa: E402
from tracehome.models import (  # noqa: E402
    Advertiser,
    AdvertiserContact,
    CreditLot,
    LedgerEntry,
    Listing,
    User,
)

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def database():
    settings = get_settings()
    admin = create_engine(
        settings.database_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    admin.dispose()
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")
    yield
    get_engine().dispose()


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with get_engine().begin() as connection:
        # TRUNCATE skips the append-only trigger; only the tests may do this.
        connection.execute(
            text(
                "TRUNCATE review_cases, leads, ledger_entries, unlocks, credit_lots, photos, "
                "listings, users, advertiser_contacts, advertisers RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def session():
    with new_session() as s:
        yield s


@pytest.fixture
def client():
    from tracehome.main import app

    return TestClient(app)


# ---- helpers that build made-up data -------------------------------------------------------


def make_advertiser(session, name="Demo Agency: Test Homes") -> Advertiser:
    advertiser = Advertiser(name=name, kind="agency")
    session.add(advertiser)
    session.flush()
    session.add(
        AdvertiserContact(
            advertiser_id=advertiser.id, phone="+251 000 000 999", email="test@example.com"
        )
    )
    session.commit()
    return advertiser


def make_advertiser_user(session, advertiser: Advertiser) -> User:
    user = User(display_name="Test advertiser", role="advertiser", advertiser_id=advertiser.id)
    session.add(user)
    session.commit()
    return user


def make_listing(session, advertiser: Advertiser, **overrides) -> Listing:
    values = dict(
        advertiser_id=advertiser.id,
        title="2-bedroom apartment in Gerji",
        description="Made-up test listing, furnished, near the light rail.",
        purpose="rent",
        property_type="apartment",
        sub_city="Bole",
        neighborhood="Gerji",
        price_etb=25_000,
        bedrooms=2,
        area_m2=90,
        status="approved",
    )
    values.update(overrides)
    listing = Listing(**values)
    session.add(listing)
    session.commit()
    return listing


def make_seeker(session, lots=(("bonus", 1, 30),)) -> User:
    """lots: (kind, amount, days until expiry; negative = already expired; None = never)."""
    seeker = User(display_name="Test seeker", role="seeker")
    session.add(seeker)
    session.flush()
    now = datetime.now(UTC)
    for kind, amount, days in lots:
        lot = CreditLot(
            seeker_id=seeker.id,
            kind=kind,
            original_amount=amount,
            remaining=amount,
            expires_at=None if days is None else now + timedelta(days=days),
        )
        session.add(lot)
        session.flush()
        session.add(
            LedgerEntry(
                seeker_id=seeker.id,
                credit_lot_id=lot.id,
                amount=amount,
                reason="bonus_grant" if kind == "bonus" else "purchase",
            )
        )
    session.commit()
    return seeker


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {issue_token(user)}"}


def unlock_headers(user: User, key: uuid.UUID | None = None) -> dict:
    return {**auth(user), "Idempotency-Key": str(key or uuid.uuid4())}


def ledger_matches_lots(session, seeker_id: int) -> bool:
    """Invariant 4: the ledger explains every credit that remains."""
    ledger = session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.seeker_id == seeker_id
        )
    )
    remaining = session.scalar(
        select(func.coalesce(func.sum(CreditLot.remaining), 0)).where(
            CreditLot.seeker_id == seeker_id
        )
    )
    return ledger == remaining
