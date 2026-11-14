"""Seed made-up data: advertisers, listings across Addis Ababa's sub-cities, demo users, and
credits. Every name, phone number, and email is invented (decision 12). Phone numbers use a
000 prefix and emails use example.com, so none can belong to a real person.

Run: python -m seed.seed   (it does nothing if listings already exist)
"""

import html
import random
from datetime import UTC, datetime, timedelta

import boto3
from sqlalchemy import func, select

import tracehome.models  # noqa: F401
from tracehome.config import get_settings
from tracehome.db import new_session
from tracehome.models import (
    Advertiser,
    AdvertiserContact,
    CreditLot,
    LedgerEntry,
    Listing,
    Photo,
    User,
)

# Neighborhood names are illustrative, for made-up listings only.
SUB_CITIES = {
    "Bole": ["Bole Medhane Alem", "Gerji", "Atlas", "Bulbula"],
    "Yeka": ["CMC", "Megenagna", "Ayat"],
    "Kirkos": ["Kazanchis", "Meskel Flower", "Wollo Sefer"],
    "Arada": ["Piassa", "Arat Kilo"],
    "Lideta": ["Mexico", "Coca"],
    "Nifas Silk-Lafto": ["Lebu", "Jemo", "Sarbet"],
    "Kolfe Keranio": ["Ayer Tena", "Kolfe"],
    "Gullele": ["Shiro Meda", "Entoto"],
    "Addis Ketema": ["Merkato", "Sebategna"],
    "Akaky Kaliti": ["Kality", "Tulu Dimtu"],
    "Lemi Kura": ["Summit", "Figa"],
}

ADVERTISERS = [
    ("Demo Agency: Acacia Homes", "agency", "+251 000 000 101", "acacia@example.com"),
    ("Demo Agency: Jacaranda Realty", "agency", "+251 000 000 102", "jacaranda@example.com"),
    ("Demo Broker: Tewodros B.", "broker", "+251 000 000 103", "tewodros@example.com"),
    ("Demo Owner: Almaz K.", "owner", "+251 000 000 104", "almaz@example.com"),
    ("Demo Owner: Yonas T.", "owner", "+251 000 000 105", "yonas@example.com"),
]

FEATURES = [
    "furnished",
    "unfurnished",
    "near the light rail",
    "secure compound",
    "parking for one car",
    "24-hour water tank",
    "backup generator",
    "balcony with a city view",
    "close to schools",
    "quiet street",
    "newly renovated kitchen",
    "shared garden",
]

TYPES = ["apartment", "condominium", "house", "villa", "studio"]
COLORS = ["#2f6f73", "#7a4e2d", "#3d5a80", "#6a4c93", "#8a5a44", "#2d6a4f", "#9c6644"]


def _listing(rng: random.Random, advertiser_id: int) -> Listing:
    sub_city = rng.choice(list(SUB_CITIES))
    neighborhood = rng.choice(SUB_CITIES[sub_city])
    property_type = rng.choice(TYPES)
    bedrooms = 0 if property_type == "studio" else rng.randint(1, 5)
    purpose = "rent" if rng.random() < 0.7 else "sale"  # renting drives volume (decision 2)
    if purpose == "rent":
        price = rng.randrange(8_000, 150_000, 500)  # ETB per month
    else:
        price = rng.randrange(2_500_000, 60_000_000, 50_000)  # ETB
    area = rng.randint(30, 60) if property_type == "studio" else rng.randint(55, 450)
    features = rng.sample(FEATURES, 3)
    if property_type == "studio":
        title = f"Studio in {neighborhood}"
    else:
        title = f"{bedrooms}-bedroom {property_type} in {neighborhood}"
    return Listing(
        advertiser_id=advertiser_id,
        title=title,
        description=(
            f"Made-up demo listing. A {area} m² {property_type} in {neighborhood}, {sub_city}, "
            f"{'for rent' if purpose == 'rent' else 'for sale'}: {', '.join(features)}."
        ),
        purpose=purpose,
        property_type=property_type,
        sub_city=sub_city,
        neighborhood=neighborhood,
        price_etb=price,
        bedrooms=bedrooms,
        area_m2=area,
        # Mostly approved; a few others show that search only returns approved listings.
        status=rng.choices(["approved", "submitted", "removed"], weights=[92, 5, 3])[0],
    )


def _placeholder_svg(listing: Listing, number: int, color: str) -> bytes:
    title = html.escape(listing.title)
    place = html.escape(f"{listing.neighborhood}, {listing.sub_city}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="533" viewBox="0 0 800 533">
<rect width="800" height="533" fill="{color}"/>
<path d="M250 330 L400 200 L550 330 Z" fill="#ffffff" opacity="0.25"/>
<rect x="290" y="330" width="220" height="120" fill="#ffffff" opacity="0.25"/>
<text x="400" y="90" font-family="sans-serif" font-size="30" fill="#ffffff" text-anchor="middle">{title}</text>
<text x="400" y="130" font-family="sans-serif" font-size="22" fill="#ffffff" text-anchor="middle" opacity="0.85">{place}</text>
<text x="400" y="500" font-family="sans-serif" font-size="18" fill="#ffffff" text-anchor="middle" opacity="0.7">Demo photo {number} · made-up data</text>
</svg>""".encode()


def seed(listing_count: int = 200) -> None:
    settings = get_settings()
    rng = random.Random(81)  # fixed, so every teammate gets the same data
    s3 = boto3.client("s3", region_name=settings.aws_region)

    with new_session() as session:
        if session.scalar(select(func.count()).select_from(Listing)):
            print("Database already seeded; restoring the placeholder photos only.")
        else:
            _seed_database(session, rng, listing_count)
        # LocalStack keeps nothing between restarts, but the database does. Writing the seed
        # photos every time keeps the two in step. Files go in before the database rows are
        # committed, so no approved photo ever points at a missing file.
        count = _upload_seed_photos(session, s3, settings.photos_bucket)
        session.commit()
        print(f"Wrote {count} placeholder photos to the photos bucket.")


def _seed_database(session, rng: random.Random, listing_count: int) -> None:
    advertisers = []
    for name, kind, phone, email in ADVERTISERS:
        advertiser = Advertiser(name=name, kind=kind)
        session.add(advertiser)
        session.flush()
        session.add(AdvertiserContact(advertiser_id=advertiser.id, phone=phone, email=email))
        session.add(
            User(
                display_name=name.split(": ")[1],
                role="advertiser",
                advertiser_id=advertiser.id,
            )
        )
        advertisers.append(advertiser)

    now = datetime.now(UTC)
    seekers = [
        # (name, [(kind, amount, expires_at, created_at)]). Hana: 3 bonus. Dawit: 1 bonus + 2
        # purchased. Selam: her bonus credits expired yesterday, so she can't unlock anything.
        ("Hana", [("bonus", 3, now + timedelta(days=90), now)]),
        (
            "Dawit",
            [("bonus", 1, now + timedelta(days=30), now), ("purchased", 2, None, now)],
        ),
        (
            "Selam",
            [("bonus", 2, now - timedelta(days=1), now - timedelta(days=91))],
        ),
    ]
    for name, lots in seekers:
        seeker = User(display_name=name, role="seeker")
        session.add(seeker)
        session.flush()
        for kind, amount, expires_at, created_at in lots:
            lot = CreditLot(
                seeker_id=seeker.id,
                kind=kind,
                original_amount=amount,
                remaining=amount,
                expires_at=expires_at,
                created_at=created_at,
            )
            session.add(lot)
            session.flush()
            # Every credit that exists has a ledger entry (invariant 4).
            session.add(
                LedgerEntry(
                    seeker_id=seeker.id,
                    credit_lot_id=lot.id,
                    amount=amount,
                    reason="bonus_grant" if kind == "bonus" else "purchase",
                    created_at=created_at,
                )
            )

    photo_count = 0
    for i in range(listing_count):
        listing = _listing(rng, rng.choice(advertisers).id)
        listing.created_at = now - timedelta(hours=i * 3)
        session.add(listing)
        session.flush()
        for number in range(1, rng.randint(1, 3) + 1):
            public_key = f"photos/{listing.id}/seed-{number}.svg"
            session.add(
                Photo(
                    listing_id=listing.id,
                    object_key=f"seed/{listing.id}/{number}.svg",
                    content_type="image/svg+xml",
                    status="approved",
                    public_key=public_key,
                    decided_at=now,
                )
            )
            photo_count += 1
    session.flush()
    print(
        f"Seeded {len(advertisers)} advertisers, {len(seekers)} seekers, "
        f"{listing_count} listings, {photo_count} photos."
    )


def _upload_seed_photos(session, s3, bucket: str) -> int:
    rows = session.execute(
        select(Photo, Listing)
        .join(Listing, Listing.id == Photo.listing_id)
        .where(Photo.object_key.startswith("seed/"))
    ).all()
    for photo, listing in rows:
        number = int(photo.object_key.rsplit("/", 1)[1].split(".")[0])
        color = COLORS[listing.id % len(COLORS)]
        s3.put_object(
            Bucket=bucket,
            Key=photo.public_key,
            Body=_placeholder_svg(listing, number, color),
            ContentType="image/svg+xml",
        )
    return len(rows)


if __name__ == "__main__":
    seed()
