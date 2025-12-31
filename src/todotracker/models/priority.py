"""Priority level model with customizable names."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from todotracker.models.base import Base


# Default priority level names
DEFAULT_PRIORITY_NAMES = {
    1: "Lowest",
    2: "Very Low",
    3: "Low",
    4: "Below Normal",
    5: "Normal",
    6: "Above Normal",
    7: "High",
    8: "Very High",
    9: "Critical",
    10: "Urgent",
}

DEFAULT_PRIORITY_COLORS = {
    1: "#9E9E9E",  # Gray
    2: "#8BC34A",  # Light Green
    3: "#4CAF50",  # Green
    4: "#CDDC39",  # Lime
    5: "#FFEB3B",  # Yellow
    6: "#FFC107",  # Amber
    7: "#FF9800",  # Orange
    8: "#FF5722",  # Deep Orange
    9: "#F44336",  # Red
    10: "#B71C1C",  # Dark Red
}


class PriorityLevel(Base):
    """Customizable priority level definitions."""

    __tablename__ = "priority_levels"

    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))

    def __repr__(self) -> str:
        return f"<PriorityLevel(level={self.level}, name={self.name!r})>"

    @classmethod
    def get_defaults(cls) -> list["PriorityLevel"]:
        """Get default priority levels for initial database seeding."""
        return [
            cls(
                level=level,
                name=name,
                color=DEFAULT_PRIORITY_COLORS.get(level),
            )
            for level, name in DEFAULT_PRIORITY_NAMES.items()
        ]
