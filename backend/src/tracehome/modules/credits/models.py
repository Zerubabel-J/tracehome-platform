import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from tracehome.db import Base


class CreditLot(Base):
    """A batch of credits. Bonus lots expire; purchased lots never do (decisions 17 and 20)."""

    __tablename__ = "credit_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str]  # bonus | purchased
    original_amount: Mapped[int]
    remaining: Mapped[int]
    expires_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class LedgerEntry(Base):
    """A permanent record of a credit change. Append-only (a database trigger enforces it)."""

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    credit_lot_id: Mapped[int] = mapped_column(ForeignKey("credit_lots.id"))
    amount: Mapped[int]
    reason: Mapped[str]  # bonus_grant | purchase | unlock
    unlock_id: Mapped[int | None] = mapped_column(ForeignKey("unlocks.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Unlock(Base):
    __tablename__ = "unlocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    credit_lot_id: Mapped[int] = mapped_column(ForeignKey("credit_lots.id"))
    request_id: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    unlock_id: Mapped[int] = mapped_column(ForeignKey("unlocks.id"))
    advertiser_id: Mapped[int] = mapped_column(ForeignKey("advertisers.id"))
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    seeker_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
