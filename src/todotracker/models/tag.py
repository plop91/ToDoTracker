"""Tag model for flexible labeling of todos."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from todotracker.models.base import Base


class Tag(Base):
    """Tag for flexible labeling of todos."""

    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))  # Hex color
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    todos: Mapped[list["Todo"]] = relationship(  # noqa: F821
        secondary="todo_tags",
        back_populates="tags",
    )

    def __repr__(self) -> str:
        return f"<Tag(name={self.name!r})>"
