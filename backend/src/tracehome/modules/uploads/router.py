import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tracehome.auth import require_advertiser
from tracehome.config import get_settings
from tracehome.db import get_session
from tracehome.modules.accounts.models import User
from tracehome.modules.listings.models import Listing, Photo
from tracehome.modules.listings.router import PhotoStatus
from tracehome.modules.uploads.storage import presign_photo_upload

router = APIRouter(prefix="/api/advertiser", tags=["uploads"])

ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


class UploadRequest(BaseModel):
    content_type: str
    size_bytes: int = Field(gt=0)


class PresignedPost(BaseModel):
    url: str
    fields: dict[str, str]


class UploadTicket(BaseModel):
    photo_id: int
    status: str
    upload: PresignedPost
    expires_in: int


def _not_found() -> HTTPException:
    return HTTPException(404, {"code": "not_found", "message": "Listing not found."})


@router.post("/listings/{listing_id}/photo-uploads", response_model=UploadTicket)
def request_photo_upload(
    listing_id: int,
    body: UploadRequest,
    user: User = Depends(require_advertiser),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    if body.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            422, {"code": "unsupported_type", "message": "Upload a JPEG, PNG, or WebP photo."}
        )
    # The browser's size is only a hint; the presigned POST policy makes S3 enforce the limit.
    if body.size_bytes > settings.max_photo_bytes:
        raise HTTPException(422, {"code": "too_large", "message": "Photos must be 5 MB or less."})

    # Rule: an advertiser can only add photos to their own listing (invariant 12). Another
    # advertiser's listing looks exactly like a missing one, so IDs reveal nothing.
    # FOR UPDATE makes two uploads to the same listing take turns, so the limit check below
    # can't be beaten by sending requests at the same moment.
    listing = session.scalar(
        select(Listing).where(Listing.id == listing_id).with_for_update()
    )
    if listing is None or listing.advertiser_id != user.advertiser_id:
        raise _not_found()

    # Rule: a listing has at most this many photos that aren't rejected.
    count = session.scalar(
        select(func.count())
        .select_from(Photo)
        .where(Photo.listing_id == listing_id, Photo.status != "rejected")
    )
    if count >= settings.max_photos_per_listing:
        raise HTTPException(
            409, {"code": "photo_limit", "message": "This listing already has the most photos."}
        )

    # Uploads land under uploads/ in the private incoming bucket. Only that prefix is scanned,
    # and only that prefix is deleted after 1 day (decisions 69 and 75).
    object_key = f"uploads/{listing_id}/{uuid.uuid4()}{ALLOWED_TYPES[body.content_type]}"
    photo = Photo(listing_id=listing_id, object_key=object_key, content_type=body.content_type)
    session.add(photo)
    session.flush()
    upload = presign_photo_upload(object_key, body.content_type)
    session.commit()
    return UploadTicket(
        photo_id=photo.id,
        status="checking",
        upload=PresignedPost(url=upload["url"], fields=upload["fields"]),
        expires_in=settings.upload_url_ttl_seconds,
    )


@router.get("/photos/{photo_id}", response_model=PhotoStatus)
def photo_status(
    photo_id: int,
    user: User = Depends(require_advertiser),
    session: Session = Depends(get_session),
):
    row = session.execute(
        select(Photo, Listing.advertiser_id)
        .join(Listing, Listing.id == Photo.listing_id)
        .where(Photo.id == photo_id)
    ).one_or_none()
    if row is None or row[1] != user.advertiser_id:
        raise HTTPException(404, {"code": "not_found", "message": "Photo not found."})
    photo = row[0]
    return PhotoStatus(
        id=photo.id,
        status=photo.status,
        reason=photo.reason,
        url=photo.url,
        created_at=photo.created_at,
    )
