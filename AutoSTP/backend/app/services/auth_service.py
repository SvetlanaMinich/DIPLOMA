"""Регистрация, вход и обновление токенов."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token_ignore_exp,
    decode_token_safe,
    hash_password,
    verify_password,
)
from app.models.audit import AuditAction
from app.models.role import Role
from app.models.session import Session as RefreshSession
from app.models.user import User
from app.schemas.auth import LogoutRequest, RefreshRequest, TokenResponse, UserLogin, UserRegister
from app.utils.audit import write_audit_log


async def get_or_create_role(
    session: AsyncSession, *, title: str, description: str | None = None
) -> Role:
    res = await session.execute(select(Role).where(Role.title == title))
    existing = res.scalar_one_or_none()
    if existing is not None:
        return existing
    role = Role(title=title, description=description)
    session.add(role)
    await session.flush()
    return role


async def register_user(session: AsyncSession, body: UserRegister) -> User:
    await get_or_create_role(session, title="student", description="Студент")
    res = await session.execute(select(Role).where(Role.title == "student"))
    student = res.scalar_one()
    email = str(body.email).lower().strip()
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role_id=student.id,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже зарегистрирован",
        )
    res = await session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.role_obj))
    )
    return res.scalar_one()


async def login_user(session: AsyncSession, body: UserLogin) -> TokenResponse:
    email = str(body.email).lower().strip()
    res = await session.execute(
        select(User).where(User.email == email).options(selectinload(User.role_obj))
    )
    user = res.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    jti = str(uuid4())
    refresh = create_refresh_token(user_id=user.id, jti=jti)
    access = create_access_token(user_id=user.id)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session.add(RefreshSession(user_id=user.id, refresh_token=jti, expires_at=expires_at))
    await write_audit_log(session, user_id=user.id, action=AuditAction.LOGIN, log_msg="Успешный вход")
    await session.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


async def refresh_tokens(session: AsyncSession, body: RefreshRequest) -> TokenResponse:
    payload = decode_token_safe(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh-токен",
        )
    jti = payload.get("jti")
    sub = payload.get("sub")
    if not jti or not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh-токен",
        )
    try:
        uid = UUID(str(sub))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh-токен",
        )
    res = await session.execute(
        select(RefreshSession).where(
            RefreshSession.refresh_token == str(jti),
            RefreshSession.user_id == uid,
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия недействительна или отозвана",
        )
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия refresh-токена истёк",
        )
    new_jti = str(uuid4())
    new_refresh = create_refresh_token(user_id=uid, jti=new_jti)
    access = create_access_token(user_id=uid)
    row.refresh_token = new_jti
    row.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await session.commit()
    return TokenResponse(access_token=access, refresh_token=new_refresh)


async def logout_session(session: AsyncSession, body: LogoutRequest) -> None:
    payload = decode_token_ignore_exp(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh-токен",
        )
    jti = payload.get("jti")
    sub = payload.get("sub")
    if not jti or not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh-токен",
        )
    try:
        uid = UUID(str(sub))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh-токен",
        )
    res = await session.execute(
        select(RefreshSession).where(
            RefreshSession.refresh_token == str(jti),
            RefreshSession.user_id == uid,
        )
    )
    row = res.scalar_one_or_none()
    if row is not None:
        await session.delete(row)
        await write_audit_log(session, user_id=uid, action=AuditAction.LOGOUT, log_msg="Выход из системы")
        await session.commit()
