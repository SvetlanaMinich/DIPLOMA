"""Schemas for section hints."""
from __future__ import annotations

from pydantic import BaseModel


class HintsResponse(BaseModel):
    section_id: str
    hints: list[str]
