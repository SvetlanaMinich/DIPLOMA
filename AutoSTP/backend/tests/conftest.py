"""Pytest configuration and fixtures."""
from __future__ import annotations

import os
from typing import AsyncGenerator

# Disable rate limiting in tests
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

# До импорта app: движок в app.core.database создаётся с этим URL.
_default = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://autostp:autostp_password@localhost:5432/autostp_db",
)
if "/autostp_test_db" not in _default:
    _default = _default.replace("/autostp_db", "/autostp_test_db")
os.environ["DATABASE_URL"] = _default

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_async_session

import app.models
from app.main import app as fastapi_app

TEST_DATABASE_URL = settings.DATABASE_URL

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
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    fastapi_app.dependency_overrides[get_async_session] = override_get_async_session
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.pop(get_async_session, None)


@pytest.fixture
def uploads_dir(tmp_path, monkeypatch):
    """Redirect UPLOAD_DIR to a temp folder and return its Path."""
    from app.core.config import settings
    root = tmp_path / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(root))
    return root


async def register_and_login_headers(
    client: AsyncClient,
    *,
    email: str = "docs@example.com",
    password: str = "ValidPass1",
    full_name: str = "Тест",
) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
