"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from todotracker.config import get_settings


# Lazy initialization of database engine and session maker
# This avoids creating connections at import time, improving testability
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine (lazy initialization)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
        )
    return _engine


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session maker (lazy initialization)."""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions.

    Handles transaction commit/rollback and cleans up any pending
    file attachments on rollback to prevent orphaned files.
    """
    async with get_async_session_maker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            # Clean up any pending attachment files before rollback
            # Attachments store their file path in _pending_file_path
            # when created, so we can clean them up on failure
            for obj in session.new:
                if hasattr(obj, "_pending_file_path"):
                    file_path = obj._pending_file_path
                    if file_path.exists():
                        try:
                            file_path.unlink()
                        except OSError:
                            pass  # Best effort cleanup
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database tables."""
    from todotracker.models import Base

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _engine, _async_session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_maker = None


def reset_db_state() -> None:
    """Reset database state for testing.

    This clears the cached engine and session maker, allowing tests
    to configure a fresh database connection.
    """
    global _engine, _async_session_maker
    _engine = None
    _async_session_maker = None
