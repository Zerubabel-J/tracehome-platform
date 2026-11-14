"""Alembic environment. Migrations are hand-written SQL, so no autogenerate metadata is needed.

On AWS this runs as a one-off ECS task from the same image: `alembic upgrade head`.
"""

from alembic import context
from sqlalchemy import create_engine

from tracehome.config import get_settings


def run_migrations_online() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        # PostgreSQL runs DDL inside a transaction, so a failed migration leaves nothing half done.
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline mode is not used. Run `alembic upgrade head`.")
run_migrations_online()
