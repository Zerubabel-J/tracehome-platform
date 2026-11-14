"""Search, listing detail, leads, and sign-in."""

from datetime import UTC, datetime, timedelta

import jwt

from tests.conftest import (
    auth,
    make_advertiser,
    make_advertiser_user,
    make_listing,
    make_seeker,
    unlock_headers,
)
from tracehome.config import get_settings
from tracehome.models import Photo


def test_search_returns_only_approved_listings(client, session):
    advertiser = make_advertiser(session)
    make_listing(session, advertiser, title="Approved villa", status="approved")
    make_listing(session, advertiser, title="Submitted villa", status="submitted")
    make_listing(session, advertiser, title="Removed villa", status="removed")

    body = client.get("/api/listings").json()

    assert [item["title"] for item in body["items"]] == ["Approved villa"]
    assert body["total"] == 1


def test_full_text_search_and_filters(client, session):
    advertiser = make_advertiser(session)
    make_listing(session, advertiser, title="Furnished apartment in Kazanchis",
                 sub_city="Kirkos", neighborhood="Kazanchis", price_etb=40_000)
    make_listing(session, advertiser, title="Family house in Ayat",
                 sub_city="Yeka", neighborhood="Ayat", property_type="house", price_etb=90_000)
    make_listing(session, advertiser, title="Villa for sale in Ayat", sub_city="Yeka",
                 neighborhood="Ayat", purpose="sale", property_type="villa", price_etb=30_000_000)

    def titles(**params):
        return [i["title"] for i in client.get("/api/listings", params=params).json()["items"]]

    assert titles(q="kazanchis") == ["Furnished apartment in Kazanchis"]
    assert titles(q="houses") == ["Family house in Ayat"]  # stemming: houses -> house
    assert sorted(titles(sub_city="Yeka")) == ["Family house in Ayat", "Villa for sale in Ayat"]
    assert titles(sub_city="Yeka", purpose="rent") == ["Family house in Ayat"]
    assert titles(max_price=50_000) == ["Furnished apartment in Kazanchis"]


def test_listing_detail_shows_approved_photos_and_never_the_contact(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser)
    session.add_all([
        Photo(listing_id=listing.id, object_key="seed/a.svg", content_type="image/svg+xml",
              status="approved", public_key=f"photos/{listing.id}/a.svg"),
        Photo(listing_id=listing.id, object_key="uploads/b.jpg", content_type="image/jpeg",
              status="checking"),
        Photo(listing_id=listing.id, object_key="uploads/c.jpg", content_type="image/jpeg",
              status="under_review"),
    ])
    session.commit()

    response = client.get(f"/api/listings/{listing.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["photo_urls"] == [f"/photos/{listing.id}/a.svg"]
    assert "000 000 999" not in response.text and "example.com" not in response.text


def test_a_removed_listing_is_not_found(client, session):
    advertiser = make_advertiser(session)
    listing = make_listing(session, advertiser, status="removed")
    assert client.get(f"/api/listings/{listing.id}").status_code == 404


def test_advertisers_see_only_their_own_leads(client, session):
    """Invariant 12: an advertiser never sees another advertiser's private data."""
    mine = make_advertiser(session, name="Demo Agency: Mine")
    theirs = make_advertiser(session, name="Demo Agency: Theirs")
    my_listing = make_listing(session, mine, title="My listing")
    their_listing = make_listing(session, theirs, title="Their listing")
    seeker = make_seeker(session, lots=[("bonus", 2, 30)])
    for listing in (my_listing, their_listing):
        client.post(f"/api/listings/{listing.id}/unlock", headers=unlock_headers(seeker))
    me = make_advertiser_user(session, mine)

    leads = client.get("/api/advertiser/leads", headers=auth(me)).json()

    assert [lead["listing_title"] for lead in leads] == ["My listing"]


def test_seekers_cannot_read_leads(client, session):
    seeker = make_seeker(session)
    assert client.get("/api/advertiser/leads", headers=auth(seeker)).status_code == 403


def test_demo_sign_in_returns_a_working_token(client, session):
    seeker = make_seeker(session, lots=[("bonus", 3, 30)])

    signed_in = client.post("/api/auth/demo-sign-in", json={"user_id": seeker.id}).json()
    me = client.get("/api/me", headers={"Authorization": f"Bearer {signed_in['token']}"})

    assert signed_in["expires_in"] == 300
    assert me.status_code == 200 and me.json()["balance"] == 3


def test_requests_without_a_valid_token_are_refused(client, session):
    seeker = make_seeker(session)
    expired = jwt.encode(
        {"sub": str(seeker.id), "exp": datetime.now(UTC) - timedelta(seconds=1)},
        get_settings().token_signing_key,
        algorithm="HS256",
    )
    forged = jwt.encode({"sub": str(seeker.id)}, "a-different-key-that-the-server-never-uses", algorithm="HS256")

    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/api/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_a_deactivated_user_loses_access_at_once(client, session):
    seeker = make_seeker(session)
    headers = auth(seeker)
    seeker.is_active = False
    session.commit()
    assert client.get("/api/me", headers=headers).status_code == 401


def test_api_responses_are_never_cached_by_default(client):
    response = client.get("/api/health")
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"


def test_demo_user_menu_shows_the_live_balance(client, session):
    seeker = make_seeker(session, lots=[("bonus", 1, 30), ("bonus", 4, -1)])  # 4 expired
    advertiser = make_advertiser(session, name="Demo Agency: Menu Homes")
    make_advertiser_user(session, advertiser)

    options = {u["id"]: u["hint"] for u in client.get("/api/auth/demo-users").json()}

    assert options[seeker.id] == "seeker, 1 credit"
    assert "advertiser, Demo Agency: Menu Homes" in options.values()


def test_database_url_carries_the_ssl_mode():
    from tracehome.config import Settings

    assert Settings(db_sslmode="require").database_url.query["sslmode"] == "require"
