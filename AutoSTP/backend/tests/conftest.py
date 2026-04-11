"""Pytest configuration and fixtures."""
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base

import app.models
from app.main import app as fastapi_app

TEST_DATABASE_URL = settings.DATABASE_URL.replace("/autostp_db", "/autostp_test_db")

# NullPool — это режим без пула: при каждом "взятии" соединения открывается новое, при "возврате" оно закрывается.
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Чистая схема на каждый тест (избегает конфликтов session-scoped async + asyncpg)."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
