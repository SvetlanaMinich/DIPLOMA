"""Generate content hints for a document section using LLM."""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.document_content import Section, TextElement
from app.prompts import hints as hint_prompts
from app.services import openrouter_service

logger = logging.getLogger(__name__)

_HINTS_TIMEOUT_S = 30.0
_MAX_SECTION_CHARS = 2_000


async def generate_hints(
    session: AsyncSession,
    user_id: UUID,
    document_id: UUID,
    section_id: UUID,
) -> list[str]:
    # Load document (verify ownership)
    doc_res = await session.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = doc_res.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    # Load section with text elements
    sec_res = await session.execute(
        select(Section)
        .where(Section.id == section_id, Section.document_id == document_id)
        .options(selectinload(Section.text_elements))
    )
    section = sec_res.scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден")

    section_text = " ".join(
        (te.content or "").strip()
        for te in sorted(section.text_elements, key=lambda e: e.order_number)
    )
    section_text = section_text[:_MAX_SECTION_CHARS]

    topic = doc.title or "не указана"

    user_msg = (
        hint_prompts.HINTS_PROMPT
        .replace("__TITLE__", section.title)
        .replace("__ROLE__", section.section_type)
        .replace("__TOPIC__", topic)
        .replace("__TEXT__", section_text or "(пустой раздел)")
    )

    try:
        raw = await asyncio.wait_for(
            openrouter_service.chat_completion(
                messages=[
                    {"role": "system", "content": hint_prompts.SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.4,
                max_tokens=512,
            ),
            timeout=_HINTS_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="LLM не ответил вовремя. Попробуйте позже.",
        )
    except openrouter_service.OpenRouterRequestError as exc:
        logger.error("LLM hints error for section %s: %s", section_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ошибка при обращении к LLM.",
        )

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]

    try:
        hints = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON from LLM for hints (section %s): %r", section_id, raw[:200])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM вернул невалидный ответ.",
        )

    if not isinstance(hints, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM вернул неожиданный формат.",
        )

    return [str(h) for h in hints if h]
