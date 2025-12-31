"""Priority level schemas."""

from pydantic import Field

from todotracker.schemas.base import BaseSchema


class PriorityLevelUpdate(BaseSchema):
    """Schema for updating a priority level."""

    name: str | None = Field(None, min_length=1, max_length=50)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class PriorityLevelResponse(BaseSchema):
    """Schema for priority level responses."""

    level: int
    name: str
    color: str | None
