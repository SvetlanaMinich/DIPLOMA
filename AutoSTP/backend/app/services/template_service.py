"""Template CRUD and rule-extraction service."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

import docx
from fastapi import UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template, TemplateType
from app.models.user import User
from app.prompts import template_extraction
from app.schemas.template import (
    TemplateConfiguration,
    TemplateCreate,
    TemplateUpdate,
)
from app.services import openrouter_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


async def create_template(
    session: AsyncSession,
    user: User,
    template_in: TemplateCreate,
) -> Template:
    if template_in.type == TemplateType.SYSTEM and user.role != "admin":
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания системного шаблона",
        )

    db_obj = Template(
        user_id=None if template_in.type == TemplateType.SYSTEM else user.id,
        name=template_in.name,
        description=template_in.description,
        type=template_in.type,
        template_json=template_in.template_json.model_dump(),
    )
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj


async def get_template(
    session: AsyncSession,
    template_id: UUID,
    user: Optional[User] = None,
) -> Template:
    from fastapi import HTTPException

    result = await session.execute(select(Template).where(Template.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")
    if template.type == TemplateType.PERSONAL:
        if not user or template.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этому персональному шаблону",
            )
    return template


async def get_templates(
    session: AsyncSession,
    user: User,
    skip: int = 0,
    limit: int = 100,
    type_filter: Optional[TemplateType] = None,
) -> tuple[List[Template], int]:
    filters: list = []
    if type_filter == TemplateType.SYSTEM:
        filters.append(Template.type == TemplateType.SYSTEM)
    elif type_filter == TemplateType.PERSONAL:
        filters.append((Template.type == TemplateType.PERSONAL) & (Template.user_id == user.id))
    else:
        filters.append((Template.type == TemplateType.SYSTEM) | (Template.user_id == user.id))

    count_stmt = select(func.count()).select_from(Template).where(*filters)
    total_res = await session.execute(count_stmt)
    total = int(total_res.scalar_one() or 0)

    stmt = (
        select(Template)
        .where(*filters)
        .order_by(Template.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await session.execute(stmt)
    items = list(res.scalars().all())
    return items, total


async def update_template(
    session: AsyncSession,
    template_id: UUID,
    user: User,
    template_in: TemplateUpdate,
) -> Template:
    from fastapi import HTTPException

    template = await get_template(session, template_id, user)
    if template.type == TemplateType.SYSTEM and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут изменять системные шаблоны",
        )

    update_data = template_in.model_dump(exclude_unset=True)
    if "template_json" in update_data and template_in.template_json is not None:
        template.template_json = template_in.template_json.model_dump()
    if "name" in update_data:
        template.name = update_data["name"]
    if "description" in update_data:
        template.description = update_data["description"]

    await session.commit()
    await session.refresh(template)
    return template


async def delete_template(
    session: AsyncSession,
    template_id: UUID,
    user: User,
) -> None:
    template = await get_template(session, template_id, user)
    if template.type == TemplateType.SYSTEM and user.role != "admin":
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут удалять системные шаблоны",
        )
    await session.delete(template)
    await session.commit()


# ---------------------------------------------------------------------------
# Text extraction from file bytes
# ---------------------------------------------------------------------------


def _extract_text_pdfplumber(content: bytes) -> str:
    """Extract text from PDF using pdfplumber (better layout handling)."""
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = (page.extract_text(x_tolerance=3, y_tolerance=3) or "").strip()
            if text:
                pages.append(f"--- PAGE {i + 1} ---\n{text}")
    return "\n\n".join(pages)


def _extract_text_pypdf2(content: bytes) -> str:
    """Fallback PDF extraction using PyPDF2."""
    import PyPDF2

    reader = PyPDF2.PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"--- PAGE {i + 1} ---\n{text}")
    return "\n\n".join(pages)


def extract_text_from_bytes(content: bytes, filename: str) -> str:
    """Extract plain text from DOCX, PDF, or TXT bytes."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "docx":
        doc = docx.Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    if ext == "pdf":
        try:
            text = _extract_text_pdfplumber(content)
            if len(text.strip()) > 200:
                return text
        except Exception as e:
            logger.warning("pdfplumber failed, falling back to PyPDF2: %s", e)
        return _extract_text_pypdf2(content)

    if ext == "txt":
        return content.decode("utf-8", errors="replace")

    raise ValueError(f"Unsupported file format: .{ext}")


# Keep old name as alias for callers that imported it directly
_extract_text_from_bytes = extract_text_from_bytes


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

# Patterns that mark the start of a "formatting rules" section.
# The negative lookahead (?!\s*\.{4,}) excludes TOC entries (which have ".......... N").
_FORMAT_SECTION_START_RE = re.compile(
    r"(?:^|[\n\r])\s*(?:2\s+)?(?:ТРЕБОВАНИЯ\s+К\s+ПОЯСНИТЕЛЬНОЙ"
    r"|Требования\s+к\s+пояснительной"
    r"|ОФОРМЛЕНИЕ\s+(?:ТЕКСТОВЫХ|ПОЯСНИТЕЛЬНОЙ)"
    r"|Оформление\s+(?:текстовых|пояснительной))"
    r"(?!\s*\.{4,})",   # NOT a TOC dotted-leader line
    re.IGNORECASE | re.MULTILINE,
)

# Patterns that mark the END of the formatting section (start of section 3).
_FORMAT_SECTION_END_RE = re.compile(
    r"(?:^|[\n\r])\s*3\s+(?:ТРЕБОВАНИЯ\s+К\s+ОФОРМЛЕНИЮ\s+ГРАФИЧЕСК"
    r"|Требования\s+к\s+оформлению\s+графическ"
    r"|ТРЕБОВАНИЯ\s+К\s+ГРАФИЧЕСК)"
    r"(?!\s*\.{4,})",
    re.IGNORECASE | re.MULTILINE,
)


def _is_toc_line(text: str, match_start: int) -> bool:
    """Return True if the match is a TOC entry (has dot-leaders on the same line)."""
    # Skip leading whitespace/newlines to find the actual content start
    content_start = match_start
    while content_start < len(text) and text[content_start] in ("\n", "\r", " ", "\t"):
        content_start += 1
    line_end = text.find("\n", content_start)
    if line_end == -1:
        line_end = len(text)
    line = text[content_start:line_end]
    # TOC lines have 4+ consecutive dots (dot-leaders) or end with a page number
    return bool(re.search(r"\.{4,}|\s{3,}\d+\s*$", line))


def find_formatting_section(text: str, max_chars: int = 80_000) -> str:
    """
    Return the portion of the document that contains formatting rules.

    Strategy:
      1. Find all occurrences of the section-2 heading pattern.
      2. Skip TOC entries (lines with dot-leaders like "Section ...... 19").
      3. Use the first non-TOC occurrence as the start.
      4. Use the next section heading as the end (also skipping TOC entries).
    Falls back to the first max_chars characters if nothing is found.
    """
    # Find start: first non-TOC occurrence of the section-2 heading
    start = None
    for m in _FORMAT_SECTION_START_RE.finditer(text):
        if not _is_toc_line(text, m.start()):
            start = m.start()
            break

    if start is None:
        logger.info("Formatting section boundary not found; using first %d chars", max_chars)
        return text[:max_chars]

    # Find end: first non-TOC occurrence of a section-3 heading after start
    end = None
    for m in _FORMAT_SECTION_END_RE.finditer(text, start + 100):
        if not _is_toc_line(text, m.start()):
            end = m.start()
            break

    if end is None:
        end = min(start + max_chars, len(text))

    section = text[start:end]
    logger.info(
        "Formatting section found: chars %d-%d (%d chars total)",
        start, end, len(section),
    )
    return section


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def make_chunks(text: str, chunk_size: int = 5_000, overlap: int = 500) -> list[str]:
    """Split *text* into overlapping chunks of *chunk_size* characters."""
    if not text:
        return []
    step = max(chunk_size - overlap, 1)
    return [text[i: i + chunk_size] for i in range(0, len(text), step)]


# ---------------------------------------------------------------------------
# LLM interaction helpers
# ---------------------------------------------------------------------------


def _clean_llm_json(raw: str) -> str:
    """Strip markdown fences and trailing commas from LLM output."""
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```")[0]
    # Remove trailing commas before closing braces/brackets
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    return raw.strip()


def _deep_merge(base: dict, update: dict) -> None:
    """Merge *update* into *base* in-place, skipping null/empty values."""
    for key, value in update.items():
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                continue
            if key in base and isinstance(base[key], list):
                # For extra_rules and work_structure: append without duplicates
                existing = base[key]
                for item in value:
                    if item not in existing:
                        existing.append(item)
                continue
        if isinstance(value, str) and not value.strip():
            continue
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


async def _call_llm_for_chunk(chunk: str) -> dict:
    """Run the comprehensive extraction prompt on one text chunk."""
    prompt = template_extraction.COMPREHENSIVE_PROMPT.replace("__TEXT_PLACEHOLDER__", chunk)
    raw = await openrouter_service.chat_completion(
        messages=[
            {"role": "system", "content": template_extraction.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )
    cleaned = _clean_llm_json(raw)
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# STP defaults
# ---------------------------------------------------------------------------


def _apply_stp_defaults(cfg: dict) -> None:
    """Fill in well-known BSUIR STP-01-2024 defaults for fields still null."""
    p = cfg.setdefault("page", {})
    p.setdefault("size", "A4")
    p.setdefault("page_number_pos", "bottom_right")
    if p.get("first_page_numbered") is None:
        p["first_page_numbered"] = False

    f = cfg.setdefault("fonts", {})
    if not f.get("text_alignment") or f["text_alignment"] in ("по ширине", "по ширине страницы"):
        f["text_alignment"] = "justify"
    # Fix common LLM mistake: 125 instead of 12.5 mm
    ind = f.get("paragraph_indent_mm")
    if ind is not None and ind > 25:
        f["paragraph_indent_mm"] = round(ind / 10.0, 1)
    # Normalise line_height: if it looks like points (>5), store as pt separately
    lh = f.get("line_height")
    if lh is not None and lh > 5 and f.get("line_height_pt") is None:
        f["line_height_pt"] = lh
        f["line_height"] = round(lh / 14.0, 2)

    h = cfg.setdefault("headers", {})
    h1 = h.setdefault("level_1", {})
    if h1.get("uppercase") is None:
        h1["uppercase"] = True
    if h1.get("bold") is None:
        h1["bold"] = True
    if h1.get("new_page") is None:
        h1["new_page"] = True
    h1.setdefault("font_size_pt", 14.0)
    if h1.get("numbered") is None:
        h1["numbered"] = True

    h2 = h.setdefault("level_2", {})
    if h2.get("bold") is None:
        h2["bold"] = True
    h2.setdefault("font_size_pt", 14.0)
    if h2.get("alignment") is None:
        h2["alignment"] = "left"
    if h2.get("numbered") is None:
        h2["numbered"] = True

    toc = cfg.setdefault("table_of_contents", {})
    toc.setdefault("title", "СОДЕРЖАНИЕ")
    if toc.get("title_uppercase") is None:
        toc["title_uppercase"] = True
    if toc.get("title_bold") is None:
        toc["title_bold"] = True
    toc.setdefault("title_alignment", "center")
    if toc.get("dot_leader") is None:
        toc["dot_leader"] = True
    if toc.get("include_subsections") is None:
        toc["include_subsections"] = True

    lst = cfg.setdefault("lists", {})
    if not lst.get("simple_marker") or lst["simple_marker"] in ("тире", "-"):
        lst["simple_marker"] = "–"
    if lst.get("semicolon_after_simple") is None:
        lst["semicolon_after_simple"] = True
    if lst.get("period_after_complex") is None:
        lst["period_after_complex"] = True
    lst.setdefault("sub_list_marker", "а)")
    lst.setdefault("sub_sub_marker", "1)")

    tbl = cfg.setdefault("tables", {})
    tbl.setdefault("caption_pos", "top")
    tbl.setdefault("caption_alignment", "left")
    tbl.setdefault("caption_word", "Таблица")
    tbl.setdefault("caption_separator", "–")
    if tbl.get("border_left") is None:
        tbl["border_left"] = True
    if tbl.get("border_right") is None:
        tbl["border_right"] = True
    if tbl.get("border_bottom") is None:
        tbl["border_bottom"] = True
    if tbl.get("header_bold") is None:
        tbl["header_bold"] = True
    tbl.setdefault("numbering_style", "per_section")
    tbl.setdefault("continuation_label", "Продолжение таблицы")

    img = cfg.setdefault("images", {})
    img.setdefault("caption_pos", "bottom")
    img.setdefault("caption_alignment", "center")
    img.setdefault("caption_prefix", "Рисунок")
    img.setdefault("caption_separator", "–")
    if img.get("center") is None:
        img["center"] = True

    fm = cfg.setdefault("formulas", {})
    fm.setdefault("alignment", "center")
    fm.setdefault("numbering_alignment", "right")
    if fm.get("numbering_per_section") is None:
        fm["numbering_per_section"] = True
    if fm.get("separated_by_blank_lines") is None:
        fm["separated_by_blank_lines"] = True
    fm.setdefault("explanation_starts_with", "где")

    bib = cfg.setdefault("bibliography", {})
    bib.setdefault("title", "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ")
    if bib.get("title_uppercase") is None:
        bib["title_uppercase"] = True
    bib.setdefault("title_alignment", "center")
    if bib.get("title_new_page") is None:
        bib["title_new_page"] = True
    bib.setdefault("citation_style", "square_brackets_number")
    bib.setdefault("ordering", "order_of_appearance")

    ap = cfg.setdefault("appendix", {})
    ap.setdefault("label_word", "ПРИЛОЖЕНИЕ")
    if ap.get("label_uppercase") is None:
        ap["label_uppercase"] = True
    ap.setdefault("label_alignment", "center")
    if ap.get("new_page") is None:
        ap["new_page"] = True

    fn = cfg.setdefault("footnotes", {})
    if fn.get("separator_line") is None:
        fn["separator_line"] = True


# ---------------------------------------------------------------------------
# Main extraction pipeline
# ---------------------------------------------------------------------------


async def extract_template_from_file(
    file_content: bytes,
    filename: str,
) -> TemplateConfiguration:
    """
    Full pipeline:
      1. Extract plain text from the file (pdfplumber → PyPDF2 → docx).
      2. Isolate the formatting-rules section of the document.
      3. Split into overlapping chunks and run the comprehensive LLM prompt on each.
      4. Deep-merge all partial results.
      5. Fill in known STP-01-2024 defaults for any fields still null.
      6. Return a validated TemplateConfiguration.
    """
    text = extract_text_from_bytes(file_content, filename)
    if not text.strip():
        raise ValueError("File is empty or contains no extractable text")

    logger.info("Extracted %d chars from '%s'", len(text), filename)

    # Step 2: find the relevant section
    section_text = find_formatting_section(text)
    logger.info("Formatting section: %d chars", len(section_text))

    # Step 3: chunk and call LLM
    chunks = make_chunks(section_text, chunk_size=5_000, overlap=500)
    logger.info("Processing %d chunks with comprehensive prompt", len(chunks))

    final_config: dict = {}
    final_config.setdefault("extra_rules", [])

    for idx, chunk in enumerate(chunks):
        logger.info("Chunk %d/%d (%d chars)", idx + 1, len(chunks), len(chunk))
        try:
            result = await _call_llm_for_chunk(chunk)
            _deep_merge(final_config, result)
        except json.JSONDecodeError as e:
            logger.warning("Chunk %d: JSON parse error: %s", idx + 1, e)
        except Exception as e:
            logger.warning("Chunk %d: extraction failed: %s", idx + 1, e)

        # Brief pause to avoid rate-limit bursts
        if idx < len(chunks) - 1:
            await asyncio.sleep(0.8)

    # Step 5: fill defaults
    _apply_stp_defaults(final_config)

    logger.info(
        "Extraction complete. extra_rules count: %d",
        len(final_config.get("extra_rules", [])),
    )
    return TemplateConfiguration(**final_config)


async def extract_and_save_template(
    session: AsyncSession,
    user: User,
    file_content: bytes,
    filename: str,
    name: str | None = None,
) -> Template:
    config = await extract_template_from_file(file_content, filename)

    template_name = name or f"Извлечённый из {filename}"
    db_obj = Template(
        user_id=user.id,
        name=template_name,
        type=TemplateType.PERSONAL,
        template_json=config.model_dump(),
    )
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj
