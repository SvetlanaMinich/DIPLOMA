"""Эндпоинты /api/v1/auth/*."""
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_async_session
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.auth import LogoutRequest, RefreshRequest, TokenResponse, UserLogin, UserMe, UserRegister
from app.services.auth_service import login_user, logout_session, refresh_tokens, register_user

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegister,
    session: AsyncSession = Depends(get_async_session),
) -> UserMe:
    user = await register_user(session, body)
    assert user.role_obj is not None
    return UserMe(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role_obj.title,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(
    request: Request,
    body: UserLogin,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    return await login_user(session, body)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    return await refresh_tokens(session, body)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    body: LogoutRequest,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    await logout_session(session, body)
    return {"detail": "logged out"}


@router.get("/me", response_model=UserMe)
async def me(current: User = Depends(get_current_user)) -> UserMe:
    assert current.role_obj is not None
    return UserMe(
        id=str(current.id),
        email=current.email,
        full_name=current.full_name,
        role=current.role_obj.title,
    )
