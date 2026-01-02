"""Pytest configuration and fixtures."""

import asyncio
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from todotracker.models import Base
from todotracker.main import create_app
from todotracker.database import get_db, reset_db_state
from todotracker.services.todo_service import PriorityService
from todotracker.services.cache import priority_cache
from todotracker.config import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_caches():
    """Reset all caches and database state before each test for isolation."""
    priority_cache.invalidate()
    reset_db_state()

    # Disable rate limiting for tests
    settings = get_settings()
    original_rate_limit_enabled = settings.rate_limit_enabled
    settings.rate_limit_enabled = False

    yield

    # Restore original settings
    settings.rate_limit_enabled = original_rate_limit_enabled
    priority_cache.invalidate()
    reset_db_state()


@pytest.fixture
def test_attachments_dir(tmp_path):
    """Create a temporary directory for attachments during tests."""
    attachments_dir = tmp_path / "attachments"
    attachments_dir.mkdir()

    # Patch the settings to use the temp directory
    settings = get_settings()
    original_dir = settings.attachments_dir
    settings.attachments_dir = attachments_dir

    yield attachments_dir

    # Restore original
    settings.attachments_dir = original_dir


@pytest.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        # Seed priority levels
        priority_service = PriorityService(session)
        await priority_service.seed_defaults()
        await session.commit()
        yield session


@pytest.fixture
async def client(test_engine):
    """Create a test client with overridden database."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Seed priority levels once
    async with async_session_maker() as session:
        priority_service = PriorityService(session)
        await priority_service.seed_defaults()
        await session.commit()

    async def override_get_db():
        async with async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
