"""Configuration management for ToDoTracker."""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def is_homeassistant() -> bool:
    """Check if running inside Home Assistant add-on environment."""
    return os.environ.get("SUPERVISOR_TOKEN") is not None


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="TODOTRACKER_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Application
    app_name: str = "ToDoTracker"
    debug: bool = False

    # Paths
    data_dir: Path = Path("data")
    attachments_dir: Path = Path("data/attachments")
    frontend_dir: Path | None = None

    # Database
    database_url: str = "sqlite+aiosqlite:///data/todotracker.db"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Authentication (optional - disabled by default)
    # Set TODOTRACKER_API_KEY to enable API key authentication
    api_key: str | None = None

    # File upload security
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB default
    allowed_file_extensions: set[str] = {
        # Documents
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".odt", ".ods", ".odp", ".txt", ".rtf", ".csv",
        # Images (note: .svg excluded - can contain JavaScript/XSS vectors)
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".ico",
        # Archives
        ".zip", ".tar", ".gz", ".7z", ".rar",
        # Other common formats
        ".json", ".xml", ".yaml", ".yml", ".md", ".html", ".css",
    }

    # Subtask constraints
    max_subtask_depth: int = 5  # Maximum nesting depth for subtasks

    # Rate limiting (requests per minute)
    rate_limit_enabled: bool = True
    rate_limit_default: str = "60/minute"  # Default rate limit for most endpoints
    rate_limit_uploads: str = "10/minute"  # Stricter limit for file uploads
    rate_limit_auth: str = "5/minute"  # Very strict for auth-related endpoints

    # CORS (Cross-Origin Resource Sharing)
    cors_enabled: bool = True
    cors_allow_origins: list[str] = []  # Empty = same-origin only; use ["*"] for any origin
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]
    cors_allow_credentials: bool = False  # Set True if using cookies/auth headers
    cors_max_age: int = 600  # Preflight cache duration in seconds

    @property
    def is_homeassistant(self) -> bool:
        """Check if running in Home Assistant environment."""
        return is_homeassistant()

    def setup_directories(self) -> None:
        """Ensure required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.setup_directories()
    return settings
