"""Административные маршруты."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_admin
from app.core.database import get_async_session
from app.models.document import Document
from app.models.document_content import AISuggestion
from app.models.role import Role
from app.models.user import User
from app.schemas.admin import AdminStats, PatchUserRequest, UserListItem, UserListResponse

router = APIRouter()


def _user_to_item(u: User) -> UserListItem:
    return UserListItem(
        id=str(u.id),
        email=u.email,
        full_name=u.full_name,
        role=u.role_obj.title if u.role_obj else "unknown",
        is_active=u.is_active,
        created_at=u.created_at,
    )


@router.get("/ping")
async def admin_ping(_admin: User = Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok"}


@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> UserListResponse:
    total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    res = await session.execute(
        select(User)
        .options(selectinload(User.role_obj))
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    users = res.scalars().all()
    return UserListResponse(
        items=[_user_to_item(u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch("/users/{user_id}", response_model=UserListItem)
async def patch_user(
    user_id: UUID,
    body: PatchUserRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> UserListItem:
    res = await session.execute(
        select(User).where(User.id == user_id).options(selectinload(User.role_obj))
    )
    target = res.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    if body.is_active is not None:
        target.is_active = body.is_active

    if body.role is not None:
        role_res = await session.execute(select(Role).where(Role.title == body.role))
        role = role_res.scalar_one_or_none()
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Роль '{body.role}' не найдена",
            )
        target.role_id = role.id
        target.role_obj = role

    await session.commit()
    await session.refresh(target, ["role_obj"])
    return _user_to_item(target)


@router.get("/stats", response_model=AdminStats)
async def get_stats(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> AdminStats:
    users_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    docs_count = (await session.execute(select(func.count()).select_from(Document))).scalar_one()
    ai_count = (await session.execute(select(func.count()).select_from(AISuggestion))).scalar_one()
    return AdminStats(
        total_users=users_count,
        total_documents=docs_count,
        total_ai_suggestions=ai_count,
    )
