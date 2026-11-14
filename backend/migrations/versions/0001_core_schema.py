"""Core schema: accounts, listings, photos, credits, unlocks, leads, review cases.

Written as plain SQL on purpose, so every rule the database enforces is visible in one place
(decision 40: money and permission rules are also enforced inside the database).

Revision ID: 0001
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

STATEMENTS = [
    """
    CREATE TABLE advertisers (
        id          bigserial PRIMARY KEY,
        name        text NOT NULL,
        kind        text NOT NULL CHECK (kind IN ('owner', 'broker', 'agency')),
        created_at  timestamptz NOT NULL DEFAULT now()
    )
    """,
    # Rule: personal data is kept apart from everything else, so it could move later (principle 6).
    # Contact details are only ever read by the unlock flow.
    """
    CREATE TABLE advertiser_contacts (
        advertiser_id  bigint PRIMARY KEY REFERENCES advertisers (id),
        phone          text NOT NULL,
        email          text NOT NULL
    )
    """,
    # Rule: an advertiser account always belongs to an advertiser, and a seeker account never does.
    """
    CREATE TABLE users (
        id             bigserial PRIMARY KEY,
        display_name   text NOT NULL,
        role           text NOT NULL CHECK (role IN ('seeker', 'advertiser')),
        advertiser_id  bigint REFERENCES advertisers (id),
        is_active      boolean NOT NULL DEFAULT true,
        created_at     timestamptz NOT NULL DEFAULT now(),
        CHECK ((role = 'advertiser') = (advertiser_id IS NOT NULL))
    )
    """,
    # Search runs inside PostgreSQL (decision 62): a generated tsvector column with a GIN index is
    # never out of date, so there is no indexer to run.
    """
    CREATE TABLE listings (
        id             bigserial PRIMARY KEY,
        advertiser_id  bigint NOT NULL REFERENCES advertisers (id),
        title          text NOT NULL,
        description    text NOT NULL,
        purpose        text NOT NULL CHECK (purpose IN ('rent', 'sale')),
        property_type  text NOT NULL
                       CHECK (property_type IN ('apartment', 'condominium', 'house', 'villa', 'studio')),
        sub_city       text NOT NULL,
        neighborhood   text NOT NULL,
        price_etb      integer NOT NULL CHECK (price_etb > 0),
        bedrooms       smallint NOT NULL CHECK (bedrooms >= 0),
        area_m2        integer NOT NULL CHECK (area_m2 > 0),
        status         text NOT NULL DEFAULT 'submitted'
                       CHECK (status IN ('submitted', 'approved', 'removed')),
        created_at     timestamptz NOT NULL DEFAULT now(),
        search_vector  tsvector GENERATED ALWAYS AS (
            setweight(to_tsvector('english', title), 'A') ||
            setweight(to_tsvector('english', neighborhood || ' ' || sub_city), 'B') ||
            setweight(to_tsvector('english', description), 'C')
        ) STORED
    )
    """,
    "CREATE INDEX listings_search_idx ON listings USING gin (search_vector)",
    "CREATE INDEX listings_browse_idx ON listings (status, sub_city, purpose, price_etb)",
    # Rule: a photo is public only after the checks approve it, and an approved photo always has
    # a public address (decision 51).
    """
    CREATE TABLE photos (
        id              bigserial PRIMARY KEY,
        listing_id      bigint NOT NULL REFERENCES listings (id),
        object_key      text NOT NULL UNIQUE,
        object_version  text,
        content_type    text NOT NULL,
        status          text NOT NULL DEFAULT 'checking'
                        CHECK (status IN ('checking', 'approved', 'under_review', 'rejected')),
        reason          text,
        public_key      text,
        created_at      timestamptz NOT NULL DEFAULT now(),
        decided_at      timestamptz,
        CHECK (status <> 'approved' OR public_key IS NOT NULL)
    )
    """,
    "CREATE INDEX photos_listing_idx ON photos (listing_id, status)",
    # Rules on credit lots:
    # - a balance never goes negative, even if the code has a bug (invariant 1)
    # - bonus credits always expire and purchased credits never do (decisions 17 and 20)
    """
    CREATE TABLE credit_lots (
        id               bigserial PRIMARY KEY,
        seeker_id        bigint NOT NULL REFERENCES users (id),
        kind             text NOT NULL CHECK (kind IN ('bonus', 'purchased')),
        original_amount  integer NOT NULL CHECK (original_amount > 0),
        remaining        integer NOT NULL,
        expires_at       timestamptz,
        created_at       timestamptz NOT NULL DEFAULT now(),
        CHECK (remaining >= 0 AND remaining <= original_amount),
        CHECK ((kind = 'bonus') = (expires_at IS NOT NULL))
    )
    """,
    "CREATE INDEX credit_lots_seeker_idx ON credit_lots (seeker_id)",
    # Rules on unlocks:
    # - a seeker never pays twice for the same listing: UNIQUE (seeker_id, listing_id) (invariant 3)
    # - a retried request is never charged twice: UNIQUE (request_id) (invariant 2)
    """
    CREATE TABLE unlocks (
        id             bigserial PRIMARY KEY,
        seeker_id      bigint NOT NULL REFERENCES users (id),
        listing_id     bigint NOT NULL REFERENCES listings (id),
        credit_lot_id  bigint NOT NULL REFERENCES credit_lots (id),
        request_id     uuid NOT NULL UNIQUE,
        created_at     timestamptz NOT NULL DEFAULT now(),
        UNIQUE (seeker_id, listing_id)
    )
    """,
    # Rule: every credit change is a permanent ledger entry (principle 8). An unlock entry always
    # points to its unlock, and each unlock has exactly one entry.
    """
    CREATE TABLE ledger_entries (
        id             bigserial PRIMARY KEY,
        seeker_id      bigint NOT NULL REFERENCES users (id),
        credit_lot_id  bigint NOT NULL REFERENCES credit_lots (id),
        amount         integer NOT NULL CHECK (amount <> 0),
        reason         text NOT NULL CHECK (reason IN ('bonus_grant', 'purchase', 'unlock')),
        unlock_id      bigint UNIQUE REFERENCES unlocks (id),
        created_at     timestamptz NOT NULL DEFAULT now(),
        CHECK ((reason = 'unlock') = (unlock_id IS NOT NULL))
    )
    """,
    # Rule: ledger entries can't be changed or deleted, only added (principle 8). The trigger
    # stops UPDATE and DELETE. (TRUNCATE skips row triggers, so the application's database role
    # must not be allowed to TRUNCATE. The tests use TRUNCATE to reset tables.)
    """
    CREATE FUNCTION forbid_change() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'this table is append-only: rows cannot be updated or deleted';
    END
    $$
    """,
    """
    CREATE TRIGGER ledger_entries_append_only
        BEFORE UPDATE OR DELETE ON ledger_entries
        FOR EACH ROW EXECUTE FUNCTION forbid_change()
    """,
    # Rule: every unlock produces exactly one lead for the advertiser, saved in the same
    # transaction (invariant 13, decision 70).
    """
    CREATE TABLE leads (
        id             bigserial PRIMARY KEY,
        unlock_id      bigint NOT NULL UNIQUE REFERENCES unlocks (id),
        advertiser_id  bigint NOT NULL REFERENCES advertisers (id),
        listing_id     bigint NOT NULL REFERENCES listings (id),
        seeker_id      bigint NOT NULL REFERENCES users (id),
        created_at     timestamptz NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX leads_advertiser_idx ON leads (advertiser_id, created_at DESC)",
    # Rule: one review case per flagged photo, even if the same result message arrives twice
    # (SQS delivers at least once).
    """
    CREATE TABLE review_cases (
        id          bigserial PRIMARY KEY,
        kind        text NOT NULL CHECK (kind IN ('photo')),
        photo_id    bigint NOT NULL UNIQUE REFERENCES photos (id),
        reason      text NOT NULL,
        status      text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
        created_at  timestamptz NOT NULL DEFAULT now()
    )
    """,
]


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for table in [
        "review_cases",
        "leads",
        "ledger_entries",
        "unlocks",
        "credit_lots",
        "photos",
        "listings",
        "users",
        "advertiser_contacts",
        "advertisers",
    ]:
        op.execute(f"DROP TABLE {table}")
    op.execute("DROP FUNCTION forbid_change()")
