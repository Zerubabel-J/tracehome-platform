from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracehome.auth import require_advertiser
from tracehome.db import get_session
from tracehome.modules.accounts.models import Advertiser, User
from tracehome.modules.listings.models import Listing, Photo

router = APIRouter(prefix="/api", tags=["listings"])

PAGE_SIZE = 20


class ListingSummary(BaseModel):
    id: int
    title: str
    purpose: str
    property_type: str
    sub_city: str
    neighborhood: str
    price_etb: int
    bedrooms: int
    area_m2: int
    cover_photo_url: str | None


class ListingDetail(ListingSummary):
    description: str
    advertiser_name: str
    advertiser_kind: str
    photo_urls: list[str]
    created_at: datetime
    # Deliberately no contact details here: they come only from the unlock endpoint (invariant 6).
    # Nothing here depends on who is asking, which keeps this response safe to cache later.


class SearchPage(BaseModel):
    items: list[ListingSummary]
    total: int
    page: int
    page_size: int


class PhotoStatus(BaseModel):
    id: int
    status: str
    reason: str | None
    url: str | None
    created_at: datetime


class AdvertiserListing(BaseModel):
    id: int
    title: str
    status: str
    sub_city: str
    price_etb: int
    photos: list[PhotoStatus]


def _approved_photo_urls(session: Session, listing_ids: list[int]) -> dict[int, list[str]]:
    """Only approved photos are ever shown (decision 51)."""
    photos = session.scalars(
        select(Photo)
        .where(Photo.listing_id.in_(listing_ids), Photo.status == "approved")
        .order_by(Photo.listing_id, Photo.id)
    ).all()
    urls: dict[int, list[str]] = {}
    for photo in photos:
        urls.setdefault(photo.listing_id, []).append(photo.url)
    return urls


def _summary(listing: Listing, urls: dict[int, list[str]]) -> dict:
    return {
        "id": listing.id,
        "title": listing.title,
        "purpose": listing.purpose,
        "property_type": listing.property_type,
        "sub_city": listing.sub_city,
        "neighborhood": listing.neighborhood,
        "price_etb": listing.price_etb,
        "bedrooms": listing.bedrooms,
        "area_m2": listing.area_m2,
        "cover_photo_url": (urls.get(listing.id) or [None])[0],
    }


@router.get("/listings", response_model=SearchPage)
def search_listings(
    q: str | None = Query(None, max_length=100, description="Words to search for"),
    sub_city: str | None = None,
    purpose: Literal["rent", "sale"] | None = None,
    property_type: str | None = None,
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    min_bedrooms: int | None = Query(None, ge=0),
    page: int = Query(1, ge=1, le=500),
    session: Session = Depends(get_session),
):
    # Rule: only approved listings appear in search (invariant 8).
    conditions = [Listing.status == "approved"]
    if sub_city:
        conditions.append(Listing.sub_city == sub_city)
    if purpose:
        conditions.append(Listing.purpose == purpose)
    if property_type:
        conditions.append(Listing.property_type == property_type)
    if min_price is not None:
        conditions.append(Listing.price_etb >= min_price)
    if max_price is not None:
        conditions.append(Listing.price_etb <= max_price)
    if min_bedrooms is not None:
        conditions.append(Listing.bedrooms >= min_bedrooms)

    order_by = [Listing.created_at.desc(), Listing.id.desc()]
    if q and q.strip():
        # PostgreSQL full-text search (decision 62). websearch_to_tsquery accepts what people
        # type, such as: bole furnished -studio
        query = func.websearch_to_tsquery("english", q)
        conditions.append(Listing.search_vector.op("@@")(query))
        order_by = [func.ts_rank(Listing.search_vector, query).desc(), Listing.id.desc()]

    total = session.scalar(select(func.count()).select_from(Listing).where(*conditions))
    listings = session.scalars(
        select(Listing)
        .where(*conditions)
        .order_by(*order_by)
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    ).all()
    urls = _approved_photo_urls(session, [listing.id for listing in listings])
    return SearchPage(
        items=[ListingSummary(**_summary(listing, urls)) for listing in listings],
        total=total,
        page=page,
        page_size=PAGE_SIZE,
    )


@router.get("/listings/{listing_id}", response_model=ListingDetail)
def get_listing(listing_id: int, session: Session = Depends(get_session)):
    row = session.execute(
        select(Listing, Advertiser)
        .join(Advertiser, Advertiser.id == Listing.advertiser_id)
        .where(Listing.id == listing_id, Listing.status == "approved")
    ).one_or_none()
    if row is None:
        raise HTTPException(404, {"code": "not_found", "message": "Listing not found."})
    listing, advertiser = row
    urls = _approved_photo_urls(session, [listing.id])
    return ListingDetail(
        **_summary(listing, urls),
        description=listing.description,
        advertiser_name=advertiser.name,
        advertiser_kind=advertiser.kind,
        photo_urls=urls.get(listing.id, []),
        created_at=listing.created_at,
    )


@router.get("/advertiser/listings", response_model=list[AdvertiserListing])
def my_listings(user: User = Depends(require_advertiser), session: Session = Depends(get_session)):
    # Rule: an advertiser sees only their own listings and photo statuses (invariant 12).
    listings = session.scalars(
        select(Listing)
        .where(Listing.advertiser_id == user.advertiser_id)
        .order_by(Listing.created_at.desc(), Listing.id.desc())
    ).all()
    photos = session.scalars(
        select(Photo)
        .where(Photo.listing_id.in_([listing.id for listing in listings]))
        .order_by(Photo.id.desc())
    ).all()
    by_listing: dict[int, list[PhotoStatus]] = {}
    for photo in photos:
        by_listing.setdefault(photo.listing_id, []).append(
            PhotoStatus(
                id=photo.id,
                status=photo.status,
                reason=photo.reason,
                url=photo.url,
                created_at=photo.created_at,
            )
        )
    return [
        AdvertiserListing(
            id=listing.id,
            title=listing.title,
            status=listing.status,
            sub_city=listing.sub_city,
            price_etb=listing.price_etb,
            photos=by_listing.get(listing.id, []),
        )
        for listing in listings
    ]
