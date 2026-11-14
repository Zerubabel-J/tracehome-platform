from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from tracehome.db import Base


class Advertiser(Base):
    __tablename__ = "advertisers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    kind: Mapped[str]  # owner | broker | agency
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AdvertiserContact(Base):
    """Personal data, kept apart from everything else (principle 6)."""

    __tablename__ = "advertiser_contacts"

    advertiser_id: Mapped[int] = mapped_column(ForeignKey("advertisers.id"), primary_key=True)
    phone: Mapped[str]
    email: Mapped[str]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str]
    role: Mapped[str]  # seeker | advertiser
    advertiser_id: Mapped[int | None] = mapped_column(ForeignKey("advertisers.id"))
    is_active: Mapped[bool] = mapped_column(server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
