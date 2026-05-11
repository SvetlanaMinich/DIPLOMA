"""Schemas for document segmentation API."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class SegmentRequest(BaseModel):
    template_id: UUID = Field(..., description="ID шаблона, по которому ищем разделы")


class SectionOut(BaseModel):
    id: str
    role: str
    title: str
    level: int
    order_number: int
    text_preview: str = Field(..., description="Первые 200 символов текста раздела")
    char_count: int


class SegmentResponse(BaseModel):
    document_id: str
    template_id: str
    sections: list[SectionOut]
    total_sections: int
    unmatched_chars: int = Field(
        0, description="Символы текста, не попавшие ни в один раздел"
    )
