"""Tests for admin API (Stage 11)."""
from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Role, User
from tests.conftest import register_and_login_headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_admin(client: AsyncClient, session: AsyncSession, email: str) -> dict[str, str]:
    """Register a user, promote to admin, return auth headers."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "AdminPass1", "full_name": "Admin"},
    )
    # Ensure admin role exists
    res = await session.execute(select(Role).where(Role.title == "admin"))
    admin_role = res.scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(title="admin", description="Администратор")
        session.add(admin_role)
        await session.flush()

    # Promote user
    user_res = await session.execute(select(User).where(User.email == email))
    user = user_res.scalar_one()
    user.role_id = admin_role.id
    await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "AdminPass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Admin ping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_ping_ok(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _make_admin(client, db_session, "ping_admin@example.com")
    resp = await client.get("/api/v1/admin/ping", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_admin_ping_forbidden_for_student(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await register_and_login_headers(client, email="student_ping@example.com")
    resp = await client.get("/api/v1/admin/ping", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_ping_unauthenticated(client: AsyncClient, db_session: AsyncSession) -> None:
    resp = await client.get("/api/v1/admin/ping")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_users_ok(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _make_admin(client, db_session, "listadmin@example.com")
    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_users_response_fields(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _make_admin(client, db_session, "fieldsadmin@example.com")
    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    user = items[0]
    for field in ("id", "email", "full_name", "role", "is_active", "created_at"):
        assert field in user, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_list_users_pagination(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_h = await _make_admin(client, db_session, "paginadmin@example.com")
    # Register 3 more students
    for i in range(3):
        await register_and_login_headers(client, email=f"pagstu{i}@example.com")

    resp_all = await client.get("/api/v1/admin/users?limit=100", headers=admin_h)
    total = resp_all.json()["total"]
    assert total >= 4

    resp_page = await client.get("/api/v1/admin/users?skip=0&limit=2", headers=admin_h)
    assert resp_page.status_code == 200
    page_body = resp_page.json()
    assert len(page_body["items"]) == 2
    assert page_body["skip"] == 0
    assert page_body["limit"] == 2


@pytest.mark.asyncio
async def test_list_users_total_matches_count(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_h = await _make_admin(client, db_session, "countadmin@example.com")
    for i in range(2):
        await register_and_login_headers(client, email=f"cnt{i}@example.com")

    resp = await client.get("/api/v1/admin/users?limit=100", headers=admin_h)
    body = resp.json()
    assert body["total"] == len(body["items"])


@pytest.mark.asyncio
async def test_list_users_forbidden_for_student(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await register_and_login_headers(client, email="nolist@example.com")
    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_users_unauthenticated(client: AsyncClient, db_session: AsyncSession) -> None:
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /admin/users/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_user_promote_to_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_h = await _make_admin(client, db_session, "promoter@example.com")
    stu_h = await register_and_login_headers(client, email="promoted@example.com")

    # Find the student's ID via list
    res = await client.get("/api/v1/admin/users?limit=100", headers=admin_h)
    items = res.json()["items"]
    target = next(u for u in items if u["email"] == "promoted@example.com")
    user_id = target["id"]
    assert target["role"] == "student"

    resp = await client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"role": "admin"},
        headers=admin_h,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_patch_user_block(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_h = await _make_admin(client, db_session, "blocker@example.com")
    await register_and_login_headers(client, email="blocked@example.com")

    res = await client.get("/api/v1/admin/users?limit=100", headers=admin_h)
    target = next(u for u in res.json()["items"] if u["email"] == "blocked@example.com")
    user_id = target["id"]

    resp = await client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"is_active": False},
        headers=admin_h,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_blocked_user_gets_403(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_h = await _make_admin(client, db_session, "blkadmin@example.com")
    stu_h = await register_and_login_headers(client, email="blkuser@example.com")

    # Block the user
    res = await client.get("/api/v1/admin/users?limit=100", headers=admin_h)
    target = next(u for u in res.json()["items"] if u["email"] == "blkuser@example.com")
    await client.patch(
        f"/api/v1/admin/users/{target['id']}",
        json={"is_active": False},
        headers=admin_h,
    )

    # The blocked user's existing token should get 403 now
    resp = await client.get("/api/v1/documents", headers=stu_h)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_user_invalid_role(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_h = await _make_admin(client, db_session, "badrole@example.com")
    await register_and_login_headers(client, email="target_badrole@example.com")

    res = await client.get("/api/v1/admin/users?limit=100", headers=admin_h)
    target = next(u for u in res.json()["items"] if u["email"] == "target_badrole@example.com")

    resp = await client.patch(
        f"/api/v1/admin/users/{target['id']}",
        json={"role": "superuser"},
        headers=admin_h,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_user_404(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_h = await _make_admin(client, db_session, "notfound@example.com")
    resp = await client.patch(
        f"/api/v1/admin/users/{uuid4()}",
        json={"is_active": False},
        headers=admin_h,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_user_forbidden_for_student(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await register_and_login_headers(client, email="nopatch@example.com")
    resp = await client.patch(
        f"/api/v1/admin/users/{uuid4()}",
        json={"is_active": False},
        headers=headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stats_returns_counts(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_h = await _make_admin(client, db_session, "statsadmin@example.com")
    resp = await client.get("/api/v1/admin/stats", headers=admin_h)
    assert resp.status_code == 200
    body = resp.json()
    assert "total_users" in body
    assert "total_documents" in body
    assert "total_ai_suggestions" in body
    assert body["total_users"] >= 1
    assert body["total_documents"] >= 0
    assert body["total_ai_suggestions"] >= 0


@pytest.mark.asyncio
async def test_stats_user_count_increases(client: AsyncClient, db_session: AsyncSession) -> None:
    admin_h = await _make_admin(client, db_session, "statsinc@example.com")

    r1 = await client.get("/api/v1/admin/stats", headers=admin_h)
    count_before = r1.json()["total_users"]

    await register_and_login_headers(client, email="newstatuser@example.com")

    r2 = await client.get("/api/v1/admin/stats", headers=admin_h)
    count_after = r2.json()["total_users"]
    assert count_after == count_before + 1


@pytest.mark.asyncio
async def test_stats_forbidden_for_student(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await register_and_login_headers(client, email="nostats@example.com")
    resp = await client.get("/api/v1/admin/stats", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stats_unauthenticated(client: AsyncClient, db_session: AsyncSession) -> None:
    resp = await client.get("/api/v1/admin/stats")
    assert resp.status_code == 401
