"""Схемы API администратора."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserListItem(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    skip: int
    limit: int


class PatchUserRequest(BaseModel):
    role: str | None = Field(default=None, description="Новая роль: 'student' или 'admin'")
    is_active: bool | None = Field(default=None, description="Активность учётной записи")


class AdminStats(BaseModel):
    total_users: int
    total_documents: int
    total_ai_suggestions: int
