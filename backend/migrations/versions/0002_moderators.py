"""Moderators: a third kind of user, and a decision record on every review case.

Revision ID: 0002
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

STATEMENTS = [
    # Rule: a moderator works for TraceHome, so like a seeker it never belongs to an advertiser.
    # (The existing users_check already says: advertiser_id is set only for advertisers.)
    "ALTER TABLE users DROP CONSTRAINT users_role_check",
    """
    ALTER TABLE users ADD CONSTRAINT users_role_check
        CHECK (role IN ('seeker', 'advertiser', 'moderator'))
    """,
    # Rule: every closed case records who decided, what, and when ("a decision record",
    # requirements section on review cases). An open case has none of these; a closed one has all.
    """
    ALTER TABLE review_cases
        ADD COLUMN decision    text CHECK (decision IN ('approved', 'rejected')),
        ADD COLUMN decided_by  bigint REFERENCES users (id),
        ADD COLUMN decided_at  timestamptz,
        ADD COLUMN note        text,
        ADD CONSTRAINT review_cases_decision_record_check CHECK (
            (status = 'open') = (decision IS NULL AND decided_by IS NULL AND decided_at IS NULL)
        )
    """,
    "CREATE INDEX review_cases_open_idx ON review_cases (created_at) WHERE status = 'open'",
]


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP INDEX review_cases_open_idx")
    op.execute(
        "ALTER TABLE review_cases DROP CONSTRAINT review_cases_decision_record_check, "
        "DROP COLUMN note, DROP COLUMN decided_at, DROP COLUMN decided_by, DROP COLUMN decision"
    )
    op.execute("ALTER TABLE users DROP CONSTRAINT users_role_check")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('seeker', 'advertiser'))"
    )
