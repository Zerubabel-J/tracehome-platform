"""Recording upload results (decisions 67 and 76).

The upload checks (GuardDuty, then the Lambda function) never touch the database. They put one
message per decision on the upload results queue, and this handler records it.
"""

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from tracehome.models import Photo, ReviewCase

log = logging.getLogger(__name__)


class UnknownUpload(Exception):
    """No photo matches the message. Raising leaves the message on the queue, so after 3 tries
    it moves to the dead-letter queue, where the team sees it (decision 53)."""


class UploadResult(BaseModel):
    """The message the Lambda function sends. Version it, so the format can change safely."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["upload.checked"]
    version: Literal[1]
    object_key: str
    object_version: str | None = None
    outcome: Literal["approved", "flagged", "rejected"]
    reason: str | None = None
    public_key: str | None = None

    @model_validator(mode="after")
    def approved_photos_need_a_public_key(self):
        if self.outcome == "approved" and not (self.public_key or "").startswith("photos/"):
            raise ValueError("an approved photo needs a public_key under photos/")
        return self


def record_upload_result(session: Session, body: dict) -> str:
    """Apply one result. Returns the photo's status afterwards. The caller commits."""
    # A malformed message raises here; it is retried and then lands in the dead-letter queue.
    result = UploadResult.model_validate(body)

    photo = session.scalar(
        select(Photo).where(Photo.object_key == result.object_key).with_for_update()
    )
    if photo is None:
        raise UnknownUpload(result.object_key)

    # Rule: SQS delivers at least once, so the same result may arrive twice. Only a photo that is
    # still "checking" changes; a repeat finds it already decided and changes nothing.
    if photo.status != "checking":
        log.info("Photo %s already recorded as %s; ignoring repeat", photo.id, photo.status)
        return photo.status

    photo.object_version = result.object_version
    photo.decided_at = func.now()

    if result.outcome == "approved":
        photo.status = "approved"
        photo.public_key = result.public_key
    elif result.outcome == "flagged":
        # Rule: doubtful cases go to a person (principle 4). The photo waits in held/ and a
        # review case opens. ON CONFLICT DO NOTHING plus the UNIQUE (photo_id) constraint mean a
        # repeated message can never open a second case.
        photo.status = "under_review"
        photo.reason = result.reason or "Flagged by the automatic checks"
        session.execute(
            insert(ReviewCase)
            .values(kind="photo", photo_id=photo.id, reason=photo.reason)
            .on_conflict_do_nothing(index_elements=["photo_id"])
        )
    else:
        # Rule: a failed or unsafe check is never treated as approval (decision 66).
        photo.status = "rejected"
        photo.reason = result.reason or "Rejected by the automatic checks"

    session.flush()
    return photo.status
