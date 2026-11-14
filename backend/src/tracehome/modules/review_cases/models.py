from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from tracehome.db import Base


class ReviewCase(Base):
    """A decision that automation sends to a person (principle 4). Only photo cases for now."""

    __tablename__ = "review_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str]
    photo_id: Mapped[int] = mapped_column(ForeignKey("photos.id"))
    reason: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="open")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
