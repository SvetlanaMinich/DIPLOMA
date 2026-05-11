"""Схемы API документов."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_string: str
    created_at: datetime
    snapshot: dict[str, Any] | None


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    document_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    original_filename: str | None = None


class DocumentDetail(BaseModel):
    id: str
    title: str
    document_type: str
    status: str
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    current_version: DocumentVersionOut | None
    versions_count: int


class FormatRequest(BaseModel):
    template_id: str = Field(..., description="UUID шаблона для форматирования")


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    snapshot: dict[str, Any]


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    skip: int
    limit: int
