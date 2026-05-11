"""Tests for document export (Stage 8) — DOCX and PDF."""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.export_service import convert_docx_to_pdf
from tests.conftest import register_and_login_headers
from tests.test_segmentation import SAMPLE_TEXT, WORK_STRUCTURE_JSON, LLM_RESPONSE
from tests.test_formatting import _full_pipeline, _mock_latex_compilation, _FAKE_PDF, _FAKE_DOCX


# ---------------------------------------------------------------------------
# Unit tests — convert_docx_to_pdf
# ---------------------------------------------------------------------------

class TestConvertDocxToPdf:
    def test_raises_501_when_libreoffice_missing(self):
        from fastapi import HTTPException
        with patch("app.services.export_service.shutil.which", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                convert_docx_to_pdf(b"fake docx bytes")
            assert exc_info.value.status_code == 501

    def test_raises_500_on_libreoffice_failure(self, tmp_path):
        from fastapi import HTTPException
        fake_result = MagicMock()
        fake_result.returncode = 1
        fake_result.stderr = b"error"

        with patch("app.services.export_service.shutil.which", return_value="/usr/bin/soffice"):
            with patch("app.services.export_service.subprocess.run", return_value=fake_result):
                with pytest.raises(HTTPException) as exc_info:
                    convert_docx_to_pdf(b"fake docx bytes")
                assert exc_info.value.status_code == 500

    def test_returns_pdf_bytes_on_success(self, tmp_path):
        fake_pdf = b"%PDF-1.4 fake pdf content"
        fake_result = MagicMock()
        fake_result.returncode = 0

        def fake_run(cmd, **kwargs):
            # Simulate LibreOffice writing a PDF to the outdir
            outdir = Path(cmd[cmd.index("--outdir") + 1])
            (outdir / "document.pdf").write_bytes(fake_pdf)
            return fake_result

        with patch("app.services.export_service.shutil.which", return_value="/usr/bin/soffice"):
            with patch("app.services.export_service.subprocess.run", side_effect=fake_run):
                result = convert_docx_to_pdf(b"some docx bytes")

        assert result == fake_pdf


# ---------------------------------------------------------------------------
# Integration tests (DB + mocked LLM + mocked PDF conversion)
# ---------------------------------------------------------------------------

@pytest.fixture
def uploads_dir(tmp_path, monkeypatch):
    from app.core.config import settings
    root = tmp_path / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(root))
    return root


async def _format_pipeline(client: AsyncClient, headers: dict) -> tuple[str, str]:
    """Full pipeline: upload → segment → format. Returns (doc_id, tmpl_id)."""
    doc_id, tmpl_id = await _full_pipeline(client, headers)
    mock_pdf, mock_docx = _mock_latex_compilation()
    with mock_pdf, mock_docx:
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/format",
            json={"template_id": tmpl_id},
            headers=headers,
        )
    assert resp.status_code == 200, resp.text
    return doc_id, tmpl_id


@pytest.mark.asyncio
async def test_export_docx_returns_200(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp1@example.com")
    doc_id, _ = await _format_pipeline(client, headers)

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/docx", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_export_docx_content_type(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp2@example.com")
    doc_id, _ = await _format_pipeline(client, headers)

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/docx", headers=headers)
    ct = resp.headers["content-type"]
    assert "wordprocessingml" in ct or "openxmlformats" in ct


@pytest.mark.asyncio
async def test_export_docx_attachment_header(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp3@example.com")
    doc_id, _ = await _format_pipeline(client, headers)

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/docx", headers=headers)
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert ".docx" in resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_export_docx_valid_file(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp4@example.com")
    doc_id, _ = await _format_pipeline(client, headers)

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/docx", headers=headers)
    assert resp.status_code == 200
    assert len(resp.content) > 0


@pytest.mark.asyncio
async def test_export_docx_without_format_returns_422(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp5@example.com")
    files = {"file": ("doc.txt", SAMPLE_TEXT.encode(), "text/plain")}
    up = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    doc_id = up.json()["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/docx", headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_export_docx_404_wrong_document(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp6@example.com")
    resp = await client.get(f"/api/v1/documents/{uuid4()}/export/docx", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_docx_401_no_auth(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    resp = await client.get(f"/api/v1/documents/{uuid4()}/export/docx")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_export_docx_cannot_access_other_users(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    owner_h = await register_and_login_headers(client, email="owner3@example.com")
    attacker_h = await register_and_login_headers(client, email="attacker3@example.com", password="ValidPass2")
    doc_id, _ = await _format_pipeline(client, owner_h)

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/docx", headers=attacker_h)
    assert resp.status_code == 404


# --- PDF export ---

@pytest.mark.asyncio
async def test_export_pdf_returns_200(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp7@example.com")
    doc_id, _ = await _format_pipeline(client, headers)

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/pdf", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_export_pdf_content_type(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp8@example.com")
    doc_id, _ = await _format_pipeline(client, headers)

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/pdf", headers=headers)
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_export_pdf_attachment_header(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp9@example.com")
    doc_id, _ = await _format_pipeline(client, headers)

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/pdf", headers=headers)
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert ".pdf" in resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_export_pdf_without_format_returns_422(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp10@example.com")
    files = {"file": ("doc.txt", SAMPLE_TEXT.encode(), "text/plain")}
    up = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    doc_id = up.json()["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}/export/pdf", headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_export_pdf_404_wrong_document(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    headers = await register_and_login_headers(client, email="exp11@example.com")
    resp = await client.get(f"/api/v1/documents/{uuid4()}/export/pdf", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_pdf_401_no_auth(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    resp = await client.get(f"/api/v1/documents/{uuid4()}/export/pdf")
    assert resp.status_code == 401
