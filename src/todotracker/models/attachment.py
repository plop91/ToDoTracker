"""Attachment model for file storage."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from todotracker.models.base import Base


class Attachment(Base):
    """File attachment for a todo."""

    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    todo_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("todos.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    todo: Mapped["Todo"] = relationship(back_populates="attachments")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Attachment(original_name={self.original_name!r})>"
