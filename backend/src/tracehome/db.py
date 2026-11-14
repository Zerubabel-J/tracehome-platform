"""Database connection. PostgreSQL is the single source of truth (decision 39)."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from tracehome.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # survives an RDS failover or restart
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_pool_size,
        )
    return _engine


def new_session() -> Session:
    return Session(get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request. Anything not committed is rolled back."""
    session = new_session()
    try:
        yield session
    finally:
        session.close()
