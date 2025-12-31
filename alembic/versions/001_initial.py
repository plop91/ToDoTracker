"""Initial migration - create all tables.

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Categories table
    op.create_table(
        "categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("color", sa.String(7)),
        sa.Column("icon", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("color", sa.String(7)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Priority levels table
    op.create_table(
        "priority_levels",
        sa.Column("level", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(7)),
    )

    # Todos table
    op.create_table(
        "todos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("priority", sa.Integer, default=5),
        sa.Column("completed", sa.Boolean, default=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("todos.id", ondelete="CASCADE")),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Todo-Tag association table
    op.create_table(
        "todo_tags",
        sa.Column("todo_id", sa.String(36), sa.ForeignKey("todos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.String(36), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # Attachments table
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("todo_id", sa.String(36), sa.ForeignKey("todos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create indexes for common queries
    op.create_index("ix_todos_due_date", "todos", ["due_date"])
    op.create_index("ix_todos_priority", "todos", ["priority"])
    op.create_index("ix_todos_completed", "todos", ["completed"])
    op.create_index("ix_todos_parent_id", "todos", ["parent_id"])
    op.create_index("ix_todos_category_id", "todos", ["category_id"])


def downgrade() -> None:
    op.drop_table("attachments")
    op.drop_table("todo_tags")
    op.drop_table("todos")
    op.drop_table("priority_levels")
    op.drop_table("tags")
    op.drop_table("categories")
