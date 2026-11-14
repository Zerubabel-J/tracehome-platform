from datetime import datetime

from sqlalchemy import Computed, ForeignKey, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from tracehome.db import Base


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    advertiser_id: Mapped[int] = mapped_column(ForeignKey("advertisers.id"))
    title: Mapped[str]
    description: Mapped[str]
    purpose: Mapped[str]  # rent | sale
    property_type: Mapped[str]
    sub_city: Mapped[str]
    neighborhood: Mapped[str]
    price_etb: Mapped[int]
    bedrooms: Mapped[int]
    area_m2: Mapped[int]
    status: Mapped[str] = mapped_column(server_default="submitted")  # submitted | approved | removed
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # Filled in by PostgreSQL (see migration 0001); the application never writes it.
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, Computed("see migration 0001", persisted=True), deferred=True
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    object_key: Mapped[str]  # where the upload landed in the incoming bucket
    object_version: Mapped[str | None]
    content_type: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="checking")
    reason: Mapped[str | None]
    public_key: Mapped[str | None]  # photos/... in the photos bucket, once approved
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    decided_at: Mapped[datetime | None]

    @property
    def url(self) -> str | None:
        # CloudFront sends /photos/* to the photos bucket, so the key doubles as the path.
        return f"/{self.public_key}" if self.status == "approved" and self.public_key else None
