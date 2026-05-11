"""Tests for document segmentation (Stage 5.2)."""
from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from docx import Document
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_content import Section, TextElement
from app.services import segmentation_service
from app.services.segmentation_service import (
    _RawSegment,
    _merge_segments,
    _build_structure_description,
)
from tests.conftest import register_and_login_headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_docx(text: str) -> bytes:
    buf = BytesIO()
    d = Document()
    for para in text.split("\n\n"):
        d.add_paragraph(para.strip())
    d.save(buf)
    return buf.getvalue()


SAMPLE_TEXT = (
    "МИНИСТЕРСТВО ОБРАЗОВАНИЯ РЕСПУБЛИКИ БЕЛАРУСЬ\n\n"
    "БЕЛОРУССКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ ИНФОРМАТИКИ И РАДИОЭЛЕКТРОНИКИ\n\n"
    "ВВЕДЕНИЕ\n\n"
    "Введение содержит обоснование актуальности темы.\n\n"
    "1 АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ\n\n"
    "В данном разделе рассматривается предметная область.\n"
    "Анализируются существующие решения.\n\n"
    "ЗАКЛЮЧЕНИЕ\n\n"
    "Заключение подводит итоги работы.\n\n"
    "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ\n\n"
    "1. Иванов И.И. Информатика. – Минск: БГУИР, 2020. – 200 с.\n"
)

WORK_STRUCTURE_JSON = [
    {
        "role": "title_page",
        "title_hints": ["Титульный лист", "МИНИСТЕРСТВО ОБРАЗОВАНИЯ"],
        "required": True,
    },
    {
        "role": "introduction",
        "title_hints": ["Введение", "ВВЕДЕНИЕ"],
        "required": True,
    },
    {
        "role": "main_body",
        "title_hints": ["1 Анализ", "2 Разработка", "3 Реализация"],
        "required": True,
    },
    {
        "role": "conclusion",
        "title_hints": ["Заключение", "ЗАКЛЮЧЕНИЕ"],
        "required": True,
    },
    {
        "role": "references",
        "title_hints": ["СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", "Список источников"],
        "required": True,
    },
]

LLM_RESPONSE = json.dumps([
    {"role": "title_page", "title": "Титульный лист", "start_char": 0, "end_char": 120},
    {"role": "introduction", "title": "ВВЕДЕНИЕ", "start_char": 120, "end_char": 200},
    {"role": "main_body", "title": "1 АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ", "start_char": 200, "end_char": 330},
    {"role": "conclusion", "title": "ЗАКЛЮЧЕНИЕ", "start_char": 330, "end_char": 395},
    {"role": "references", "title": "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", "start_char": 395, "end_char": len(SAMPLE_TEXT)},
])


# ---------------------------------------------------------------------------
# Unit tests — pure logic (no DB, no LLM)
# ---------------------------------------------------------------------------

class TestMergeSegments:
    known = {"title_page", "introduction", "main_body", "conclusion", "references"}

    def test_empty_returns_fallback(self):
        result = _merge_segments([], 100, self.known)
        assert len(result) == 1
        assert result[0].role == "main_body"
        assert result[0].start_char == 0
        assert result[0].end_char == 100

    def test_deduplicates_roles_keeps_first(self):
        raw = [
            _RawSegment("introduction", "Введение", 10, 50),
            _RawSegment("introduction", "Введение dup", 55, 80),
            _RawSegment("conclusion", "Заключение", 80, 100),
        ]
        result = _merge_segments(raw, 100, self.known)
        roles = [s.role for s in result]
        assert roles.count("introduction") == 1
        assert "conclusion" in roles

    def test_fills_leading_gap(self):
        raw = [_RawSegment("introduction", "Введение", 50, 100)]
        result = _merge_segments(raw, 100, self.known)
        assert result[0].start_char == 0
        # Either a gap-filler or introduction at 0
        assert any(s.start_char == 0 for s in result)

    def test_contiguous_coverage(self):
        raw = [
            _RawSegment("introduction", "Введение", 0, 40),
            _RawSegment("main_body", "Основная часть", 40, 80),
            _RawSegment("conclusion", "Заключение", 80, 100),
        ]
        result = _merge_segments(raw, 100, self.known)
        assert result[0].start_char == 0
        assert result[-1].end_char == 100
        for i in range(len(result) - 1):
            assert result[i].end_char == result[i + 1].start_char

    def test_snaps_end_char_to_text_len(self):
        raw = [_RawSegment("introduction", "Введение", 0, 50)]
        result = _merge_segments(raw, 100, self.known)
        assert result[-1].end_char == 100

    def test_unknown_roles_filtered(self):
        raw = [
            _RawSegment("unknown_role", "???", 0, 50),
            _RawSegment("introduction", "Введение", 50, 100),
        ]
        result = _merge_segments(raw, 100, self.known)
        roles = [s.role for s in result]
        assert "unknown_role" not in roles


class TestBuildStructureDescription:
    def test_contains_roles(self):
        from app.schemas.template import SectionTemplate
        sections = [
            SectionTemplate(role="introduction", title_hints=["Введение"]),
            SectionTemplate(role="conclusion", title_hints=["Заключение"]),
        ]
        desc = _build_structure_description(sections)
        assert "introduction" in desc
        assert "conclusion" in desc
        assert "Введение" in desc

    def test_empty_sections(self):
        desc = _build_structure_description([])
        assert desc.startswith("[")


# ---------------------------------------------------------------------------
# Integration tests (DB + mocked LLM)
# ---------------------------------------------------------------------------

@pytest.fixture
def uploads_dir(tmp_path, monkeypatch):
    from app.core.config import settings
    root = tmp_path / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(root))
    return root


async def _upload_and_create_template(client: AsyncClient, headers: dict) -> tuple[str, str]:
    """Upload SAMPLE_TEXT as .txt and create a template; return (doc_id, template_id)."""
    files = {"file": ("diploma.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")}
    up = await client.post("/api/v1/documents/upload", files=files, data={"document_type": "di"}, headers=headers)
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]

    tmpl = await client.post(
        "/api/v1/templates/",
        json={
            "name": "Тест-шаблон",
            "type": "personal",
            "template_json": {"work_structure": WORK_STRUCTURE_JSON},
        },
        headers=headers,
    )
    assert tmpl.status_code == 201, tmpl.text
    tmpl_id = tmpl.json()["id"]
    return doc_id, tmpl_id


@pytest.mark.asyncio
async def test_segment_endpoint_returns_sections(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="seg1@example.com")
    doc_id, tmpl_id = await _upload_and_create_template(client, headers)

    with patch(
        "app.services.segmentation_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=LLM_RESPONSE,
    ):
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/segment",
            json={"template_id": tmpl_id},
            headers=headers,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["document_id"] == doc_id
    assert data["total_sections"] > 0
    assert len(data["sections"]) == data["total_sections"]


@pytest.mark.asyncio
async def test_segment_creates_sections_in_db(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="seg2@example.com")
    doc_id, tmpl_id = await _upload_and_create_template(client, headers)

    with patch(
        "app.services.segmentation_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=LLM_RESPONSE,
    ):
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/segment",
            json={"template_id": tmpl_id},
            headers=headers,
        )
    assert resp.status_code == 200, resp.text

    from uuid import UUID
    sections = (
        await db_session.execute(
            select(Section).where(Section.document_id == UUID(doc_id))
        )
    ).scalars().all()

    assert len(sections) >= 1
    roles = {s.section_type for s in sections}
    # At least some expected roles should be present
    assert roles & {"introduction", "main_body", "conclusion", "references"}


@pytest.mark.asyncio
async def test_segment_creates_text_elements(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="seg3@example.com")
    doc_id, tmpl_id = await _upload_and_create_template(client, headers)

    with patch(
        "app.services.segmentation_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=LLM_RESPONSE,
    ):
        await client.post(
            f"/api/v1/documents/{doc_id}/segment",
            json={"template_id": tmpl_id},
            headers=headers,
        )

    from uuid import UUID
    sections = (
        await db_session.execute(
            select(Section).where(Section.document_id == UUID(doc_id))
        )
    ).scalars().all()

    for sec in sections:
        tes = (
            await db_session.execute(
                select(TextElement).where(TextElement.section_id == sec.id)
            )
        ).scalars().all()
        assert len(tes) == 1, f"Section {sec.section_type} has no TextElement"
        assert len(tes[0].content) > 0


@pytest.mark.asyncio
async def test_segment_updates_document_status(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="seg4@example.com")
    doc_id, tmpl_id = await _upload_and_create_template(client, headers)

    with patch(
        "app.services.segmentation_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=LLM_RESPONSE,
    ):
        await client.post(
            f"/api/v1/documents/{doc_id}/segment",
            json={"template_id": tmpl_id},
            headers=headers,
        )

    doc_resp = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert doc_resp.json()["status"] == "inpr"


@pytest.mark.asyncio
async def test_segment_reruns_replace_old_sections(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="seg5@example.com")
    doc_id, tmpl_id = await _upload_and_create_template(client, headers)

    with patch(
        "app.services.segmentation_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=LLM_RESPONSE,
    ):
        await client.post(f"/api/v1/documents/{doc_id}/segment", json={"template_id": tmpl_id}, headers=headers)
        await client.post(f"/api/v1/documents/{doc_id}/segment", json={"template_id": tmpl_id}, headers=headers)

    from uuid import UUID
    sections = (
        await db_session.execute(
            select(Section).where(Section.document_id == UUID(doc_id))
        )
    ).scalars().all()
    # Should not double-up sections
    assert len(sections) == len(set(s.section_type for s in sections))


@pytest.mark.asyncio
async def test_segment_404_for_wrong_document(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="seg6@example.com")
    _, tmpl_id = await _upload_and_create_template(client, headers)
    fake_id = str(uuid4())

    resp = await client.post(
        f"/api/v1/documents/{fake_id}/segment",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_segment_404_for_wrong_template(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="seg7@example.com")
    doc_id, _ = await _upload_and_create_template(client, headers)
    fake_tmpl = str(uuid4())

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/segment",
        json={"template_id": fake_tmpl},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_segment_cannot_access_other_users_document(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    owner_h = await register_and_login_headers(client, email="owner@example.com")
    attacker_h = await register_and_login_headers(client, email="attacker@example.com", password="ValidPass2")
    doc_id, tmpl_id = await _upload_and_create_template(client, owner_h)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/segment",
        json={"template_id": tmpl_id},
        headers=attacker_h,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_segment_handles_llm_invalid_json(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="seg8@example.com")
    doc_id, tmpl_id = await _upload_and_create_template(client, headers)

    with patch(
        "app.services.segmentation_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value="не JSON вовсе",
    ):
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/segment",
            json={"template_id": tmpl_id},
            headers=headers,
        )

    # Should not crash — fallback to one "main_body" section
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sections"] >= 1


@pytest.mark.asyncio
async def test_segment_requires_auth(client: AsyncClient, db_session: AsyncSession, uploads_dir) -> None:
    resp = await client.post(
        f"/api/v1/documents/{uuid4()}/segment",
        json={"template_id": str(uuid4())},
    )
    assert resp.status_code == 401
