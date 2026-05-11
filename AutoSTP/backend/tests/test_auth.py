"""Тесты аутентификации (этап 2)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Role, User


async def seed_roles(session: AsyncSession) -> tuple[Role, Role]:
    student = Role(title="student", description="Студент")
    admin = Role(title="admin", description="Администратор")
    session.add_all([student, admin])
    await session.flush()
    return student, admin


@pytest.mark.asyncio
async def test_register_login_refresh_me(client: AsyncClient, db_session: AsyncSession) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "User@Example.com",
            "password": "ValidPass1",
            "full_name": "Тест",
        },
    )
    assert reg.status_code == 201
    body = reg.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "student"

    bad_pw = await client.post(
        "/api/v1/auth/register",
        json={"email": "u2@example.com", "password": "short1A"},
    )
    assert bad_pw.status_code == 422

    dup = await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "OtherPass1"},
    )
    assert dup.status_code == 409

    login_bad = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "WrongPass1"},
    )
    assert login_bad.status_code == 401

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "User@Example.com", "password": "ValidPass1"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"
    assert "access_token" in tokens and "refresh_token" in tokens

    me_no = await client.get("/api/v1/auth/me")
    assert me_no.status_code == 401

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    tokens2 = refreshed.json()
    assert tokens2["refresh_token"] != tokens["refresh_token"]

    old_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert old_refresh.status_code == 401


@pytest.mark.asyncio
async def test_admin_forbidden_and_allowed(client: AsyncClient, db_session: AsyncSession) -> None:
    student_role, admin_role = await seed_roles(db_session)
    await client.post(
        "/api/v1/auth/register",
        json={"email": "stu@example.com", "password": "ValidPass1", "full_name": "S"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "stu@example.com", "password": "ValidPass1"},
    )
    access = login.json()["access_token"]

    forbidden = await client.get(
        "/api/v1/admin/ping",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert forbidden.status_code == 403

    res = await db_session.execute(select(User).where(User.email == "stu@example.com"))
    u = res.scalar_one()
    u.role_id = admin_role.id
    await db_session.commit()

    ok = await client.get(
        "/api/v1/admin/ping",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert ok.status_code == 200

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "stu@example.com", "password": "ValidPass1"},
    )
    access2 = new_login.json()["access_token"]
    ok2 = await client.get(
        "/api/v1/admin/ping",
        headers={"Authorization": f"Bearer {access2}"},
    )
    assert ok2.status_code == 200


@pytest.mark.asyncio
async def test_register_after_seed_roles_no_duplicate_student_role(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await seed_roles(db_session)
    await db_session.commit()
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "ValidPass1"},
    )
    assert r.status_code == 201
    res = await db_session.execute(select(Role).where(Role.title == "student"))
    rows = res.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_logout_revokes_refresh(client: AsyncClient, db_session: AsyncSession) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "out@example.com", "password": "ValidPass1"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "out@example.com", "password": "ValidPass1"},
    )
    refresh_tok = login.json()["refresh_token"]

    out = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_tok})
    assert out.status_code == 200

    refresh_fail = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_tok},
    )
    assert refresh_fail.status_code == 401

    again = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_tok})
    assert again.status_code == 200

    bad = await client.post("/api/v1/auth/logout", json={"refresh_token": "not-a-jwt"})
    assert bad.status_code == 401
