"""Tests for document formatting (Stage 7) — LaTeX pipeline."""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentWorkflowStatus
from app.models.document_content import Section, TextElement
from app.services.formatting_service import _UNNUMBERED_ROLES
from app.schemas.template import TemplateConfiguration
from app.services.latex_service import build_template_context, render_latex
from tests.conftest import register_and_login_headers
from tests.test_segmentation import (
    SAMPLE_TEXT,
    WORK_STRUCTURE_JSON,
    LLM_RESPONSE,
)


# ---------------------------------------------------------------------------
# Unit tests — build_docx (no DB, no LLM)
# ---------------------------------------------------------------------------

def _make_sections(roles_and_texts: list[tuple[str, str]]) -> list[Section]:
    """Create in-memory Section+TextElement objects for unit tests."""
    from uuid import uuid4
    sections = []
    for i, (role, text) in enumerate(roles_and_texts):
        sec = Section()
        sec.id = uuid4()
        sec.section_type = role
        sec.title = role.replace("_", " ").title()
        sec.order_number = i
        sec.level = 1
        te = TextElement()
        te.id = uuid4()
        te.section_id = sec.id
        te.element_type = "paragraph"
        te.content = text
        te.order_number = 0
        sec.text_elements = [te]
        sections.append(sec)
    return sections


DEFAULT_CFG = TemplateConfiguration()

_FAKE_PDF = b"%PDF-1.4 fake pdf content"
_FAKE_DOCX = b"PK\x03\x04 fake docx content"


class TestLatexGeneration:
    def test_render_returns_string(self):
        sections = _make_sections([("introduction", "Текст введения.")])
        ctx = build_template_context(sections, DEFAULT_CFG)
        tex = render_latex(ctx)
        assert isinstance(tex, str)
        assert len(tex) > 0

    def test_output_contains_document_class(self):
        sections = _make_sections([("introduction", "Текст.")])
        ctx = build_template_context(sections, DEFAULT_CFG)
        tex = render_latex(ctx)
        assert "\\documentclass" in tex
        assert "14pt" in tex

    def test_output_contains_geometry(self):
        sections = _make_sections([("introduction", "Текст.")])
        ctx = build_template_context(sections, DEFAULT_CFG)
        tex = render_latex(ctx)
        assert "\\usepackage{geometry}" in tex
        assert "30.0mm" in tex

    def test_section_text_appears_in_latex(self):
        text = "Уникальный текст для проверки"
        sections = _make_sections([("introduction", text)])
        ctx = build_template_context(sections, DEFAULT_CFG)
        tex = render_latex(ctx)
        assert text in tex

    def test_heading_appears_for_each_section(self):
        sections = _make_sections([
            ("introduction", "Текст введения"),
            ("main_body", "Текст основной части"),
            ("conclusion", "Текст заключения"),
        ])
        ctx = build_template_context(sections, DEFAULT_CFG)
        tex = render_latex(ctx)
        assert "\\unnsec" in tex
        assert "\\section" in tex

    def test_multiple_sections_all_present(self):
        roles = ["title_page", "introduction", "main_body", "conclusion", "references"]
        sections = _make_sections([(r, f"Текст раздела {r}") for r in roles])
        ctx = build_template_context(sections, DEFAULT_CFG)
        tex = render_latex(ctx)
        for r in roles:
            escaped_r = r.replace("_", r"\_")
            assert escaped_r in tex

    def test_empty_section_does_not_crash(self):
        sections = _make_sections([("introduction", ""), ("conclusion", "Текст.")])
        ctx = build_template_context(sections, DEFAULT_CFG)
        tex = render_latex(ctx)
        assert isinstance(tex, str)
        assert len(tex) > 0

    def test_numbered_sections_get_number_prefix(self):
        sections = _make_sections([("main_body", "Содержание основного раздела.")])
        sections[0].title = "Анализ предметной области"
        ctx = build_template_context(sections, DEFAULT_CFG)
        tex = render_latex(ctx)
        assert "1 Анализ" in tex

    def test_unnumbered_roles_set(self):
        assert "introduction" in _UNNUMBERED_ROLES
        assert "conclusion" in _UNNUMBERED_ROLES
        assert "references" in _UNNUMBERED_ROLES
        assert "main_body" not in _UNNUMBERED_ROLES

    def test_references_section_generated(self):
        sections = _make_sections([("introduction", "Текст.")])
        ctx = build_template_context(
            sections, DEFAULT_CFG,
            references=[],
            document_title="Test",
        )
        ctx["references"] = [{"text": "Ivanov I.I. Test. -- Minsk, 2024."}]
        ctx["references_title"] = "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"
        tex = render_latex(ctx)
        assert "Ivanov" in tex
        assert "\\unnsec" in tex


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


async def _full_pipeline(client: AsyncClient, headers: dict) -> tuple[str, str]:
    """Upload → segment → return (doc_id, tmpl_id) ready for formatting."""
    files = {"file": ("diploma.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")}
    up = await client.post("/api/v1/documents/upload", files=files, data={"document_type": "di"}, headers=headers)
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]

    tmpl = await client.post(
        "/api/v1/templates/",
        json={"name": "Тест", "type": "personal", "template_json": {"work_structure": WORK_STRUCTURE_JSON}},
        headers=headers,
    )
    assert tmpl.status_code == 201, tmpl.text
    tmpl_id = tmpl.json()["id"]

    with patch(
        "app.services.segmentation_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=LLM_RESPONSE,
    ):
        seg = await client.post(
            f"/api/v1/documents/{doc_id}/segment",
            json={"template_id": tmpl_id},
            headers=headers,
        )
    assert seg.status_code == 200, seg.text

    return doc_id, tmpl_id


def _mock_latex_compilation():
    return (
        patch("app.services.formatting_service.compile_latex_to_pdf", return_value=_FAKE_PDF),
        patch("app.services.formatting_service.convert_latex_to_docx", return_value=_FAKE_DOCX),
    )


@pytest.mark.asyncio
async def test_format_returns_document_detail(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="fmt1@example.com")
    doc_id, tmpl_id = await _full_pipeline(client, headers)

    mock_pdf, mock_docx = _mock_latex_compilation()
    with mock_pdf, mock_docx:
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/format",
            json={"template_id": tmpl_id},
            headers=headers,
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == doc_id
    assert data["status"] == "formatted"


@pytest.mark.asyncio
async def test_format_saves_files(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="fmt2@example.com")
    doc_id, tmpl_id = await _full_pipeline(client, headers)

    mock_pdf, mock_docx = _mock_latex_compilation()
    with mock_pdf, mock_docx:
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/format",
            json={"template_id": tmpl_id},
            headers=headers,
        )
    assert resp.status_code == 200, resp.text
    meta = resp.json()["metadata"]
    assert "formatted_file_path" in meta
    assert "formatted_pdf_path" in meta

    docx_path = Path(uploads_dir) / meta["formatted_file_path"]
    assert docx_path.exists(), f"File not found: {docx_path}"


@pytest.mark.asyncio
async def test_format_updates_status_to_formatted(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="fmt4@example.com")
    doc_id, tmpl_id = await _full_pipeline(client, headers)

    mock_pdf, mock_docx = _mock_latex_compilation()
    with mock_pdf, mock_docx:
        await client.post(f"/api/v1/documents/{doc_id}/format", json={"template_id": tmpl_id}, headers=headers)

    detail = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert detail.json()["status"] == "formatted"


@pytest.mark.asyncio
async def test_format_without_segmentation_returns_422(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="fmt5@example.com")
    files = {"file": ("doc.txt", b"Hello", "text/plain")}
    up = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    doc_id = up.json()["id"]

    tmpl = await client.post(
        "/api/v1/templates/",
        json={"name": "T", "type": "personal", "template_json": {}},
        headers=headers,
    )
    tmpl_id = tmpl.json()["id"]

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/format",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_format_404_wrong_document(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="fmt6@example.com")
    tmpl = await client.post(
        "/api/v1/templates/",
        json={"name": "T", "type": "personal", "template_json": {}},
        headers=headers,
    )
    tmpl_id = tmpl.json()["id"]
    resp = await client.post(
        f"/api/v1/documents/{uuid4()}/format",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_format_404_wrong_template(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="fmt7@example.com")
    doc_id, _ = await _full_pipeline(client, headers)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/format",
        json={"template_id": str(uuid4())},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_format_cannot_access_other_users_document(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    owner_h = await register_and_login_headers(client, email="owner2@example.com")
    attacker_h = await register_and_login_headers(client, email="attacker2@example.com", password="ValidPass2")
    doc_id, tmpl_id = await _full_pipeline(client, owner_h)

    mock_pdf, mock_docx = _mock_latex_compilation()
    with mock_pdf, mock_docx:
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/format",
            json={"template_id": tmpl_id},
            headers=attacker_h,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_format_requires_auth(client: AsyncClient, db_session: AsyncSession, uploads_dir) -> None:
    resp = await client.post(
        f"/api/v1/documents/{uuid4()}/format",
        json={"template_id": str(uuid4())},
    )
    assert resp.status_code == 401
