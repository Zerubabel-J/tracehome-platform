"""Credits and unlocks: the money rules (principle 1, requirements section 6b).

Unlocking a contact does four things as one all-or-nothing step: take one credit, write the
ledger entry, record the unlock, and save the lead. The caller commits; if anything fails before
the commit, PostgreSQL undoes all of it.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from tracehome.modules.accounts.models import Advertiser, AdvertiserContact, User
from tracehome.modules.credits.models import CreditLot, Lead, LedgerEntry, Unlock
from tracehome.modules.listings.models import Listing


class UnlockError(Exception):
    status = 400
    code = "unlock_failed"
    message = "The contact could not be unlocked."


class NoCreditsLeft(UnlockError):
    status = 402
    code = "no_credits"
    message = "You have no credits left. Nothing was spent."


class ListingNotAvailable(UnlockError):
    status = 404
    code = "listing_not_available"
    message = "This listing is not available any more. Nothing was spent."


class IdempotencyKeyReused(UnlockError):
    status = 409
    code = "idempotency_key_reused"
    message = "This request ID was already used for a different unlock."


@dataclass
class Contact:
    advertiser_name: str
    phone: str
    email: str


@dataclass
class UnlockResult:
    unlock_id: int
    listing_id: int
    outcome: str  # "unlocked" (charged now) | "already_unlocked" | "replayed"
    charged: bool
    balance: int
    contact: Contact


def _usable(now=None):
    """A credit lot can be spent if it has credits left and hasn't expired (invariant 5)."""
    now = now if now is not None else func.now()
    return and_(
        CreditLot.remaining > 0,
        or_(CreditLot.expires_at.is_(None), CreditLot.expires_at > now),
    )


def usable_balance(session: Session, seeker_id: int) -> int:
    total = session.scalar(
        select(func.coalesce(func.sum(CreditLot.remaining), 0)).where(
            CreditLot.seeker_id == seeker_id, _usable()
        )
    )
    return int(total)


def _contact_for(session: Session, listing_id: int) -> Contact:
    advertiser, contact = session.execute(
        select(Advertiser, AdvertiserContact)
        .join(Listing, Listing.advertiser_id == Advertiser.id)
        .join(AdvertiserContact, AdvertiserContact.advertiser_id == Advertiser.id)
        .where(Listing.id == listing_id)
    ).one()
    return Contact(advertiser_name=advertiser.name, phone=contact.phone, email=contact.email)


def _result(session: Session, unlock: Unlock, outcome: str, charged: bool) -> UnlockResult:
    return UnlockResult(
        unlock_id=unlock.id,
        listing_id=unlock.listing_id,
        outcome=outcome,
        charged=charged,
        balance=usable_balance(session, unlock.seeker_id),
        contact=_contact_for(session, unlock.listing_id),
    )


def unlock_contact(
    session: Session, seeker_id: int, listing_id: int, request_id: uuid.UUID
) -> UnlockResult:
    # Rule: one seeker's unlocks run one at a time. Locking the seeker's row makes any other
    # unlock by the same seeker wait here until this transaction ends, so two taps can't both
    # see the last credit (invariant 1). Every check below then sees the other's committed work.
    session.execute(select(User.id).where(User.id == seeker_id).with_for_update())

    # Rule: a retry with the same request ID returns the first result and never charges again
    # (invariant 2).
    earlier = session.scalar(select(Unlock).where(Unlock.request_id == request_id))
    if earlier is not None:
        if earlier.seeker_id != seeker_id or earlier.listing_id != listing_id:
            raise IdempotencyKeyReused()
        return _result(session, earlier, outcome="replayed", charged=False)

    # Rule: a seeker never pays twice to unlock the same listing (invariant 3).
    existing = session.scalar(
        select(Unlock).where(Unlock.seeker_id == seeker_id, Unlock.listing_id == listing_id)
    )
    if existing is not None:
        return _result(session, existing, outcome="already_unlocked", charged=False)

    # Rule: every action checks the source of truth: the listing must be approved right now
    # (principle 2). FOR SHARE stops a moderator removing it until this transaction ends.
    listing = session.scalar(
        select(Listing).where(Listing.id == listing_id).with_for_update(read=True)
    )
    if listing is None or listing.status != "approved":
        raise ListingNotAvailable()

    # Rule: spend the soonest-expiring credit, so bonus credits go before purchased ones
    # (purchased lots have no expiry date, so they sort last), and an expired credit is never
    # spent (decision 20, invariant 5). FOR UPDATE locks the lot until we commit.
    lot = session.scalar(
        select(CreditLot)
        .where(CreditLot.seeker_id == seeker_id, _usable())
        .order_by(CreditLot.expires_at.asc().nulls_last(), CreditLot.id)
        .limit(1)
        .with_for_update()
    )
    if lot is None:
        raise NoCreditsLeft()

    # One transaction: credit, ledger, unlock, lead.
    # The check constraint "remaining >= 0" is the database's backstop if this code is ever wrong.
    lot.remaining -= 1
    unlock = Unlock(
        seeker_id=seeker_id, listing_id=listing_id, credit_lot_id=lot.id, request_id=request_id
    )
    session.add(unlock)
    session.flush()  # gives the unlock its id; the UNIQUE constraints are checked here too

    # Rule: a seeker's balance always equals the sum of their ledger entries (invariant 4).
    session.add(
        LedgerEntry(
            seeker_id=seeker_id,
            credit_lot_id=lot.id,
            amount=-1,
            reason="unlock",
            unlock_id=unlock.id,
        )
    )
    # Rule: every unlock produces a lead, saved in the same transaction, so a crash can't
    # separate them (invariant 13, decision 70).
    session.add(
        Lead(
            unlock_id=unlock.id,
            advertiser_id=listing.advertiser_id,
            listing_id=listing_id,
            seeker_id=seeker_id,
        )
    )
    session.flush()
    return _result(session, unlock, outcome="unlocked", charged=True)
