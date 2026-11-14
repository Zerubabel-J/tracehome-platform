"""Unlocking a contact: the money rules (requirements section 6b, invariants 1-6 and 13)."""

import threading
import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.conftest import (
    auth,
    ledger_matches_lots,
    make_advertiser,
    make_advertiser_user,
    make_listing,
    make_seeker,
    unlock_headers,
)
from tracehome.db import new_session
from tracehome.models import CreditLot, Lead, LedgerEntry, Unlock
from tracehome.modules.credits.service import NoCreditsLeft, unlock_contact, usable_balance


def count(session, model, **where):
    return session.scalar(select(func.count()).select_from(model).filter_by(**where))


def run_in_parallel(n, work):
    """Start n threads at the same moment, each with its own database session."""
    barrier = threading.Barrier(n)
    outcomes = [None] * n

    def worker(i):
        with new_session() as s:
            barrier.wait()
            try:
                result = work(s, i)
                s.commit()
                outcomes[i] = result.outcome
            except NoCreditsLeft:
                s.rollback()
                outcomes[i] = "no_credits"

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return outcomes


def test_unlock_spends_one_credit_and_records_all_four_things(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    seeker = make_seeker(session, lots=[("bonus", 3, 30)])

    response = client.post(f"/api/listings/{listing.id}/unlock", headers=unlock_headers(seeker))

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "unlocked" and body["charged"] is True
    assert body["balance"] == 2
    assert body["contact"]["phone"] == "+251 000 000 999"
    assert count(session, Unlock, seeker_id=seeker.id) == 1
    assert count(session, LedgerEntry, seeker_id=seeker.id, reason="unlock") == 1
    assert count(session, Lead, advertiser_id=advertiser.id) == 1  # invariant 13
    assert ledger_matches_lots(session, seeker.id)  # invariant 4


def test_ten_parallel_unlocks_with_one_credit_exactly_one_succeeds(session):
    """Invariant 1: ten different listings, tapped at the same moment, with one credit."""
    advertiser = make_advertiser(session)
    listings = [make_listing(session, advertiser, title=f"Listing {i}") for i in range(10)]
    seeker = make_seeker(session, lots=[("bonus", 1, 30)])

    outcomes = run_in_parallel(
        10, lambda s, i: unlock_contact(s, seeker.id, listings[i].id, uuid.uuid4())
    )

    assert outcomes.count("unlocked") == 1
    assert outcomes.count("no_credits") == 9
    session.expire_all()
    assert usable_balance(session, seeker.id) == 0
    assert count(session, Unlock, seeker_id=seeker.id) == 1
    assert count(session, Lead) == 1
    assert ledger_matches_lots(session, seeker.id)


def test_ten_parallel_unlocks_of_the_same_listing_charge_once(session):
    """Invariant 3: plenty of credits, ten taps on the same listing, one charge."""
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    seeker = make_seeker(session, lots=[("bonus", 10, 30)])

    outcomes = run_in_parallel(
        10, lambda s, i: unlock_contact(s, seeker.id, listing.id, uuid.uuid4())
    )

    assert outcomes.count("unlocked") == 1
    assert outcomes.count("already_unlocked") == 9
    assert usable_balance(session, seeker.id) == 9
    assert count(session, Unlock, seeker_id=seeker.id) == 1
    assert ledger_matches_lots(session, seeker.id)


def test_ten_parallel_retries_with_the_same_request_id_charge_once(session):
    """Invariant 2: the same request sent ten times at once (for example, a flaky network)."""
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    seeker = make_seeker(session, lots=[("bonus", 5, 30)])
    request_id = uuid.uuid4()

    outcomes = run_in_parallel(
        10, lambda s, i: unlock_contact(s, seeker.id, listing.id, request_id)
    )

    assert outcomes.count("unlocked") == 1
    assert outcomes.count("replayed") == 9
    assert usable_balance(session, seeker.id) == 4


def test_retry_with_the_same_idempotency_key_returns_the_first_result(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    seeker = make_seeker(session, lots=[("bonus", 2, 30)])
    headers = unlock_headers(seeker, uuid.uuid4())

    first = client.post(f"/api/listings/{listing.id}/unlock", headers=headers)
    retry = client.post(f"/api/listings/{listing.id}/unlock", headers=headers)

    assert first.json()["outcome"] == "unlocked"
    assert retry.status_code == 200
    assert retry.json()["outcome"] == "replayed" and retry.json()["charged"] is False
    assert retry.json()["unlock_id"] == first.json()["unlock_id"]
    assert retry.json()["balance"] == 1  # charged once, not twice


def test_reusing_an_idempotency_key_for_another_listing_is_refused(client, session):
    advertiser = make_advertiser(session)
    first_listing = make_listing(session, advertiser)
    other_listing = make_listing(session, advertiser, title="Another listing")
    seeker = make_seeker(session, lots=[("bonus", 2, 30)])
    headers = unlock_headers(seeker, uuid.uuid4())

    client.post(f"/api/listings/{first_listing.id}/unlock", headers=headers)
    response = client.post(f"/api/listings/{other_listing.id}/unlock", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "idempotency_key_reused"
    assert usable_balance(session, seeker.id) == 1


def test_no_credits_returns_402_and_changes_nothing(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    seeker = make_seeker(session, lots=[])

    response = client.post(f"/api/listings/{listing.id}/unlock", headers=unlock_headers(seeker))

    assert response.status_code == 402
    assert response.json()["detail"]["code"] == "no_credits"
    assert count(session, Unlock) == 0 and count(session, Lead) == 0


def test_bonus_is_spent_before_purchased_and_expired_credits_are_never_spent(client, session):
    """Decision 20 and invariant 5."""
    advertiser = make_advertiser(session)
    listings = [make_listing(session, advertiser, title=f"Listing {i}") for i in range(3)]
    seeker = make_seeker(
        session,
        lots=[("purchased", 1, None), ("bonus", 1, 10), ("bonus", 5, -1)],  # last one expired
    )
    assert usable_balance(session, seeker.id) == 2

    kinds = []
    for listing in listings:
        response = client.post(
            f"/api/listings/{listing.id}/unlock", headers=unlock_headers(seeker)
        )
        if response.status_code == 200:
            lot_id = session.scalar(
                select(Unlock.credit_lot_id).where(Unlock.id == response.json()["unlock_id"])
            )
            kinds.append(session.get(CreditLot, lot_id).kind)
        else:
            kinds.append(response.json()["detail"]["code"])

    assert kinds == ["bonus", "purchased", "no_credits"]
    expired = session.scalar(select(CreditLot).where(CreditLot.expires_at < func.now()))
    session.refresh(expired)
    assert expired.remaining == 5  # untouched


def test_a_listing_that_is_not_approved_cannot_be_unlocked(client, session):
    """Principle 2: the unlock always checks the source of truth, not a cached page."""
    advertiser = make_advertiser(session)
    removed = make_listing(session, advertiser, status="removed")
    seeker = make_seeker(session, lots=[("bonus", 1, 30)])

    response = client.post(f"/api/listings/{removed.id}/unlock", headers=unlock_headers(seeker))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "listing_not_available"
    assert usable_balance(session, seeker.id) == 1


def test_only_seekers_can_unlock(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    advertiser_user = make_advertiser_user(session, advertiser)

    response = client.post(
        f"/api/listings/{listing.id}/unlock", headers=unlock_headers(advertiser_user)
    )
    assert response.status_code == 403


def test_unlock_without_an_idempotency_key_is_rejected(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    seeker = make_seeker(session)

    response = client.post(f"/api/listings/{listing.id}/unlock", headers=auth(seeker))
    assert response.status_code == 422


def test_the_database_refuses_a_negative_balance_even_if_code_is_wrong(session):
    """Decision 40: the check constraint is a backstop for bugs."""
    seeker = make_seeker(session, lots=[("bonus", 1, 30)])
    with pytest.raises(IntegrityError):
        session.execute(
            text("UPDATE credit_lots SET remaining = -1 WHERE seeker_id = :id"), {"id": seeker.id}
        )
        session.flush()
    session.rollback()


def test_the_database_refuses_a_second_unlock_of_the_same_listing(session):
    """Decision 40: the UNIQUE constraint is a backstop if the checks were skipped."""
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    seeker = make_seeker(session, lots=[("bonus", 2, 30)])
    lot_id = session.scalar(select(CreditLot.id).where(CreditLot.seeker_id == seeker.id))
    session.add(
        Unlock(seeker_id=seeker.id, listing_id=listing.id, credit_lot_id=lot_id, request_id=uuid.uuid4())
    )
    session.commit()
    session.add(
        Unlock(seeker_id=seeker.id, listing_id=listing.id, credit_lot_id=lot_id, request_id=uuid.uuid4())
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_ledger_entries_cannot_be_changed_or_deleted(session):
    """Principle 8: the ledger is append-only."""
    make_seeker(session, lots=[("bonus", 1, 30)])
    for statement in ("UPDATE ledger_entries SET amount = 100", "DELETE FROM ledger_entries"):
        with pytest.raises(DBAPIError, match="append-only"):
            session.execute(text(statement))
        session.rollback()
