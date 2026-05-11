"""Semantic segmentation of documents using LLM."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentWorkflowStatus
from app.models.document_content import Section, TextElement
from app.models.template import Template
from app.prompts import segmentation as seg_prompts
from app.schemas.segmentation import SectionOut, SegmentResponse
from app.schemas.template import SectionTemplate, TemplateConfiguration
from app.services import openrouter_service

logger = logging.getLogger(__name__)

CHUNK_SIZE = 6_000
CHUNK_OVERLAP = 400
MAX_PARALLEL_CHUNKS = 5


@dataclass
class _RawSegment:
    """Segment as returned by LLM (absolute char offsets into full text)."""
    role: str
    title: str
    start_char: int
    end_char: int


# ---------------------------------------------------------------------------
# LLM call helpers
# ---------------------------------------------------------------------------

def _build_structure_description(sections: list[SectionTemplate]) -> str:
    lines: list[str] = []
    for s in sections:
        hints = ", ".join(f'"{h}"' for h in s.title_hints) if s.title_hints else "—"
        lines.append(f'  - role="{s.role}", title_hints=[{hints}], required={s.required}')
    return "[\n" + "\n".join(lines) + "\n]"


def _make_user_prompt(structure_desc: str, chunk: str) -> str:
    return (
        seg_prompts.SEGMENT_PROMPT
        .replace("__STRUCTURE_PLACEHOLDER__", structure_desc)
        .replace("__TEXT_LEN__", str(len(chunk)))
        .replace("__TEXT_PLACEHOLDER__", chunk)
    )


async def _call_llm_for_chunk(
    structure_desc: str,
    chunk: str,
    chunk_offset: int,
) -> list[_RawSegment]:
    """Send one chunk to LLM and return segments with absolute offsets."""
    user_msg = _make_user_prompt(structure_desc, chunk)
    try:
        raw = await openrouter_service.chat_completion(
            messages=[
                {"role": "system", "content": seg_prompts.SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=2048,
        )
    except openrouter_service.OpenRouterRequestError as exc:
        logger.error("LLM error for chunk at offset %d: %s", chunk_offset, exc)
        return []

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]

    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON from LLM for chunk at offset %d: %r", chunk_offset, raw[:200])
        return []

    if not isinstance(items, list):
        return []

    segments: list[_RawSegment] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            role = str(item["role"])
            title = str(item.get("title", role))
            sc = int(item["start_char"])
            ec = int(item["end_char"])
        except (KeyError, ValueError, TypeError):
            continue
        sc = max(0, min(sc, len(chunk)))
        ec = max(sc, min(ec, len(chunk)))
        segments.append(_RawSegment(role, title, chunk_offset + sc, chunk_offset + ec))

    return segments


# ---------------------------------------------------------------------------
# Merging raw segments from multiple chunks
# ---------------------------------------------------------------------------

def _merge_segments(
    raw: list[_RawSegment],
    text_len: int,
    known_roles: set[str],
) -> list[_RawSegment]:
    """Deduplicate, sort, and fill gaps to cover the whole text."""
    if not raw:
        return [_RawSegment("main_body", "Основная часть", 0, text_len)]

    # Keep only segments with known roles; sort by start
    valid = sorted(
        (s for s in raw if s.role in known_roles),
        key=lambda s: s.start_char,
    )

    if not valid:
        return [_RawSegment("main_body", "Основная часть", 0, text_len)]

    # Deduplicate by role — keep the first occurrence of each role
    seen_roles: dict[str, _RawSegment] = {}
    for seg in valid:
        if seg.role not in seen_roles:
            seen_roles[seg.role] = seg

    deduped = sorted(seen_roles.values(), key=lambda s: s.start_char)

    # Fill leading gap
    merged: list[_RawSegment] = []
    if deduped[0].start_char > 0:
        merged.append(_RawSegment("main_body", "Начало документа", 0, deduped[0].start_char))

    for i, seg in enumerate(deduped):
        next_start = deduped[i + 1].start_char if i + 1 < len(deduped) else text_len
        # Snap end_char to next segment's start (avoid gaps/overlaps)
        merged.append(_RawSegment(seg.role, seg.title, seg.start_char, next_start))

    # Fill trailing gap
    if merged and merged[-1].end_char < text_len:
        merged[-1] = _RawSegment(
            merged[-1].role, merged[-1].title,
            merged[-1].start_char, text_len,
        )

    return merged


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------

async def _delete_existing_sections(session: AsyncSession, document_id: UUID) -> None:
    """Remove all sections for this document before re-segmenting."""
    res = await session.execute(
        select(Section).where(Section.document_id == document_id)
    )
    for sec in res.scalars().all():
        await session.delete(sec)
    await session.flush()


async def _save_sections(
    session: AsyncSession,
    document_id: UUID,
    segments: list[_RawSegment],
    text: str,
) -> list[Section]:
    saved: list[Section] = []
    for order, seg in enumerate(segments):
        section_text = text[seg.start_char:seg.end_char]
        sec = Section(
            document_id=document_id,
            section_type=seg.role,
            title=seg.title[:512],
            order_number=order,
            level=1,
        )
        session.add(sec)
        await session.flush()

        te = TextElement(
            section_id=sec.id,
            element_type="paragraph",
            content=section_text,
            order_number=0,
        )
        session.add(te)
        saved.append(sec)

    return saved


def _section_to_out(sec: Section, text: str, start: int, end: int) -> SectionOut:
    section_text = text[start:end]
    return SectionOut(
        id=str(sec.id),
        role=sec.section_type,
        title=sec.title,
        level=sec.level,
        order_number=sec.order_number,
        text_preview=section_text[:200],
        char_count=len(section_text),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def segment_document(
    session: AsyncSession,
    user_id: UUID,
    document_id: UUID,
    template_id: UUID,
) -> SegmentResponse:
    # Load document
    doc_res = await session.execute(
        select(Document)
        .where(Document.id == document_id, Document.user_id == user_id)
        .options(selectinload(Document.current_version))
    )
    doc = doc_res.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if doc.current_version is None or not doc.current_version.snapshot:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Документ не содержит текста для сегментации",
        )

    plain_text: str = doc.current_version.snapshot.get("plain_text", "")
    if not plain_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Текст документа пустой",
        )

    # Load template
    tmpl_res = await session.execute(
        select(Template).where(Template.id == template_id)
    )
    tmpl = tmpl_res.scalar_one_or_none()
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")

    try:
        tmpl_cfg = TemplateConfiguration.model_validate(tmpl.template_json)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Не удалось разобрать шаблон: {exc}",
        ) from exc

    work_structure = tmpl_cfg.work_structure or []
    if not work_structure:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Шаблон не содержит work_structure",
        )

    known_roles = {s.role for s in work_structure}
    structure_desc = _build_structure_description(work_structure)

    # Split text into chunks
    chunks: list[tuple[str, int]] = []  # (chunk_text, chunk_offset)
    offset = 0
    while offset < len(plain_text):
        end = min(offset + CHUNK_SIZE, len(plain_text))
        # Try to snap end to a newline to avoid splitting mid-sentence
        if end < len(plain_text):
            nl = plain_text.rfind("\n", offset + CHUNK_SIZE - 200, end)
            if nl > offset:
                end = nl + 1
        chunks.append((plain_text[offset:end], offset))
        offset = end - CHUNK_OVERLAP if end < len(plain_text) else end

    logger.info("Segmenting doc %s: %d chars, %d chunks", document_id, len(plain_text), len(chunks))

    # Call LLM for each chunk (parallel, batched)
    all_raw: list[_RawSegment] = []
    for batch_start in range(0, len(chunks), MAX_PARALLEL_CHUNKS):
        batch = chunks[batch_start:batch_start + MAX_PARALLEL_CHUNKS]
        results = await asyncio.gather(
            *[_call_llm_for_chunk(structure_desc, chunk_text, chunk_offset)
              for chunk_text, chunk_offset in batch]
        )
        for segs in results:
            all_raw.extend(segs)

    # Merge
    merged = _merge_segments(all_raw, len(plain_text), known_roles)

    # Persist
    await _delete_existing_sections(session, document_id)
    saved = await _save_sections(session, document_id, merged, plain_text)

    # Update document status
    doc.status = DocumentWorkflowStatus.IN_PROGRESS
    await session.commit()

    # Build response
    out_sections: list[SectionOut] = []
    for sec, seg in zip(saved, merged):
        out_sections.append(_section_to_out(sec, plain_text, seg.start_char, seg.end_char))

    unmatched = sum(
        1 for seg in merged if seg.role not in known_roles
    )

    return SegmentResponse(
        document_id=str(document_id),
        template_id=str(template_id),
        sections=out_sections,
        total_sections=len(out_sections),
        unmatched_chars=unmatched,
    )
