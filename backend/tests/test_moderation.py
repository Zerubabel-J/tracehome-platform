"""The moderator console: flagged photos wait for a person, who decides once (principle 4)."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from tests.conftest import auth, make_advertiser, make_advertiser_user, make_listing, make_seeker
from tracehome.models import Photo, ReviewCase, User
from tracehome.modules.uploads import storage
from tracehome.worker.handlers import record_upload_result


@pytest.fixture
def moderator(session):
    user = User(display_name="Test moderator", role="moderator")
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def copies(monkeypatch):
    """Record S3 copies instead of making them (the tests have no S3)."""
    made = []
    monkeypatch.setattr(storage, "publish_held_photo", lambda key, public: made.append((key, public)))
    return made


@pytest.fixture
def flagged_case(session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    photo = Photo(listing_id=listing.id, object_key=f"uploads/{listing.id}/a.jpg",
                  content_type="image/jpeg")
    session.add(photo)
    session.commit()
    record_upload_result(session, {
        "type": "upload.checked", "version": 1, "object_key": photo.object_key,
        "outcome": "flagged", "reason": "Text detected",
    })
    session.commit()
    return session.scalar(select(ReviewCase).where(ReviewCase.photo_id == photo.id))


def decide(client, user, case_id, decision, note=None):
    return client.post(f"/api/moderation/cases/{case_id}/decision",
                       json={"decision": decision, "note": note}, headers=auth(user))


def test_only_moderators_see_the_queue(client, session, flagged_case):
    advertiser_user = make_advertiser_user(session, make_advertiser(session, "Demo Owner: X"))
    for user in (make_seeker(session), advertiser_user):
        assert client.get("/api/moderation/cases", headers=auth(user)).status_code == 403
        assert decide(client, user, flagged_case.id, "approved").status_code == 403


def test_queue_shows_the_case_with_a_short_lived_private_link(client, flagged_case, moderator):
    cases = client.get("/api/moderation/cases", headers=auth(moderator)).json()

    assert [c["id"] for c in cases] == [flagged_case.id]
    assert cases[0]["reason"] == "Text detected"
    # The link points at the held/ copy in the private bucket, and it expires.
    assert "/held/" in cases[0]["preview_url"]
    assert "X-Amz-Expires=300" in cases[0]["preview_url"]


def test_approving_publishes_the_photo_and_records_who_decided(
    client, session, flagged_case, moderator, copies
):
    response = decide(client, moderator, flagged_case.id, "approved")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "approved"
    assert body["decided_by_name"] == "Test moderator"
    assert body["preview_url"] is None  # closed cases no longer hand out links
    photo = session.get(Photo, flagged_case.photo_id)
    session.refresh(photo)
    assert photo.status == "approved"
    assert copies == [(photo.object_key, photo.public_key)]
    assert photo.public_key.startswith("photos/")


def test_rejecting_tells_the_advertiser_why(client, session, flagged_case, moderator, copies):
    decide(client, moderator, flagged_case.id, "rejected", note="Shows a phone number")

    photo = session.get(Photo, flagged_case.photo_id)
    session.refresh(photo)
    assert photo.status == "rejected"
    assert photo.reason == "Shows a phone number"
    assert copies == []  # nothing is published


def test_a_case_is_decided_only_once(client, session, flagged_case, moderator, copies):
    other = User(display_name="Second moderator", role="moderator")
    session.add(other)
    session.commit()

    # Two moderators click at the same moment: the row lock lets exactly one decide.
    with ThreadPoolExecutor(2) as pool:
        codes = sorted(pool.map(
            lambda pair: decide(client, *pair).status_code,
            [(moderator, flagged_case.id, "approved"), (other, flagged_case.id, "rejected")],
        ))
    assert codes == [200, 409]

    summary = client.get("/api/moderation/summary", headers=auth(moderator)).json()
    assert summary["open"] == 0
    assert summary["approved"] + summary["rejected"] == 1


def test_the_database_refuses_a_closed_case_without_a_decision(session, flagged_case):
    flagged_case.status = "closed"
    with pytest.raises(Exception, match="review_cases_decision_record_check"):
        session.commit()
    session.rollback()


def test_demo_menu_lists_every_kind_of_user(client, session, moderator):
    make_seeker(session)
    make_advertiser_user(session, make_advertiser(session))

    hints = {u["role"]: u for u in client.get("/api/auth/demo-users").json()}

    assert hints["moderator"]["hint"] == "moderator, TraceHome staff"
    assert hints["advertiser"]["advertiser_kind"] == "agency"
    assert hints["advertiser"]["hint"].startswith("agency, ")
