"""Todo model - the core entity of ToDoTracker."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from todotracker.models.base import Base


class TodoTag(Base):
    """Association table for Todo-Tag many-to-many relationship."""

    __tablename__ = "todo_tags"

    todo_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("todos.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Todo(Base):
    """Core todo item with support for subtasks."""

    __tablename__ = "todos"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    priority: Mapped[int] = mapped_column(Integer, default=5)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Foreign keys
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("todos.id", ondelete="CASCADE"),
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="SET NULL"),
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    parent: Mapped["Todo | None"] = relationship(
        back_populates="subtasks",
        remote_side=[id],
    )
    subtasks: Mapped[list["Todo"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    category: Mapped["Category | None"] = relationship(  # noqa: F821
        back_populates="todos",
    )
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="todo_tags",
        back_populates="todos",
    )
    attachments: Mapped[list["Attachment"]] = relationship(  # noqa: F821
        back_populates="todo",
        cascade="all, delete-orphan",
    )

    def mark_complete(self) -> None:
        """Mark the todo as completed."""
        self.completed = True
        self.completed_at = datetime.now(timezone.utc)

    def mark_incomplete(self) -> None:
        """Mark the todo as incomplete."""
        self.completed = False
        self.completed_at = None

    def __repr__(self) -> str:
        status = "done" if self.completed else "pending"
        return f"<Todo(title={self.title!r}, status={status})>"
