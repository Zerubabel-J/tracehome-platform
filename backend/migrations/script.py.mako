"""${message}

Revision ID: ${up_revision}
"""

from alembic import op

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rule: every migration must keep working with the version of the code that is still running
    # (expand first, contract in a later release). A rollback of ECS never rolls back the database.
    pass


def downgrade() -> None:
    pass
