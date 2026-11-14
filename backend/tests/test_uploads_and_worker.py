"""Photo uploads: presigned POST, and the worker recording results (decisions 51, 53, 67, 77)."""

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from tests.conftest import auth, make_advertiser, make_advertiser_user, make_listing
from tracehome.models import Photo, ReviewCase
from tracehome.worker.handlers import UnknownUpload, record_upload_result


def request_upload(client, user, listing_id, content_type="image/jpeg", size=200_000):
    return client.post(
        f"/api/advertiser/listings/{listing_id}/photo-uploads",
        json={"content_type": content_type, "size_bytes": size},
        headers=auth(user),
    )


def result(object_key, outcome, **extra):
    return {"type": "upload.checked", "version": 1, "object_key": object_key,
            "object_version": "v1", "outcome": outcome, **extra}


@pytest.fixture
def checking_photo(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    user = make_advertiser_user(session, advertiser)
    ticket = request_upload(client, user, listing.id).json()
    return session.get(Photo, ticket["photo_id"])


def test_upload_ticket_is_a_presigned_post_with_size_and_type_limits(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    user = make_advertiser_user(session, advertiser)

    response = request_upload(client, user, listing.id)

    assert response.status_code == 200
    ticket = response.json()
    assert ticket["status"] == "checking"
    fields = ticket["upload"]["fields"]
    assert fields["key"].startswith(f"uploads/{listing.id}/") and fields["key"].endswith(".jpg")
    assert fields["Content-Type"] == "image/jpeg"
    assert "policy" in fields  # S3 enforces content-length-range from this signed policy
    assert session.get(Photo, ticket["photo_id"]).status == "checking"


def test_an_advertiser_cannot_upload_to_another_advertisers_listing(client, session):
    mine = make_advertiser(session, name="Demo Agency: Mine")
    theirs = make_advertiser(session, name="Demo Agency: Theirs")
    their_listing = make_listing(session, theirs)
    me = make_advertiser_user(session, mine)

    assert request_upload(client, me, their_listing.id).status_code == 404


def test_unsupported_or_oversized_files_are_refused_before_signing(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    user = make_advertiser_user(session, advertiser)

    assert request_upload(client, user, listing.id, content_type="application/pdf").status_code == 422
    assert request_upload(client, user, listing.id, size=50_000_000).status_code == 422


def test_approved_result_publishes_the_photo(session, checking_photo):
    public_key = f"photos/{checking_photo.listing_id}/x.jpg"
    status = record_upload_result(
        session, result(checking_photo.object_key, "approved", public_key=public_key)
    )
    session.commit()

    session.refresh(checking_photo)
    assert status == "approved"
    assert checking_photo.url == f"/{public_key}"
    assert checking_photo.object_version == "v1"


def test_a_duplicate_flagged_message_opens_only_one_review_case(session, checking_photo):
    """SQS delivers at least once: the same message twice must change nothing the second time."""
    message = result(checking_photo.object_key, "flagged", reason="Phone number in photo")

    first = record_upload_result(session, message)
    session.commit()
    second = record_upload_result(session, message)
    session.commit()

    assert first == second == "under_review"
    assert session.scalar(select(func.count()).select_from(ReviewCase)) == 1


def test_a_duplicate_approved_message_changes_nothing(session, checking_photo):
    message = result(checking_photo.object_key, "approved", public_key="photos/1/a.jpg")
    record_upload_result(session, message)
    session.commit()
    session.refresh(checking_photo)
    decided_at = checking_photo.decided_at

    record_upload_result(session, message)
    session.commit()
    session.refresh(checking_photo)
    assert checking_photo.status == "approved" and checking_photo.decided_at == decided_at


def test_a_late_conflicting_message_does_not_overwrite_the_first_decision(session, checking_photo):
    record_upload_result(session, result(checking_photo.object_key, "rejected", reason="Malware"))
    session.commit()
    status = record_upload_result(
        session, result(checking_photo.object_key, "approved", public_key="photos/1/a.jpg")
    )
    session.commit()
    assert status == "rejected"


def test_a_rejected_photo_is_never_published(session, checking_photo):
    record_upload_result(session, result(checking_photo.object_key, "rejected", reason="Malware"))
    session.commit()
    session.refresh(checking_photo)
    assert checking_photo.status == "rejected" and checking_photo.url is None


def test_malformed_and_unknown_messages_raise_so_they_reach_the_dlq(session, checking_photo):
    with pytest.raises(ValidationError):
        record_upload_result(session, {"type": "upload.checked"})
    with pytest.raises(ValidationError):  # approved without a public key
        record_upload_result(session, result(checking_photo.object_key, "approved"))
    with pytest.raises(UnknownUpload):
        record_upload_result(session, result("uploads/999/missing.jpg", "rejected"))
    session.rollback()
