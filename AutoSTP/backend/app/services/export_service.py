"""Export formatted documents as DOCX or PDF (produced by LaTeX pipeline)."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document

logger = logging.getLogger(__name__)


def _upload_root() -> Path:
    return Path(settings.UPLOAD_DIR).resolve()


async def _load_owned_doc(session: AsyncSession, user_id: UUID, document_id: UUID) -> Document:
    res = await session.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = res.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    return doc


def _resolve_path(doc: Document, key: str, ext: str) -> Path:
    meta = doc.metadata_ or {}
    rel = meta.get(key)
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Документ не отформатирован. Сначала выполните форматирование.",
        )
    path = _upload_root() / rel
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Файл форматированного документа ({ext}) не найден на диске.",
        )
    return path


def convert_docx_to_pdf(docx_bytes: bytes) -> bytes:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF-конвертация недоступна: LibreOffice не установлен на сервере.",
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        docx_path = tmp_path / "document.docx"
        docx_path.write_bytes(docx_bytes)

        result = subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(docx_path)],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("LibreOffice conversion failed: %s", result.stderr.decode(errors="replace"))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при конвертации в PDF.",
            )

        pdf_path = tmp_path / "document.pdf"
        if not pdf_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF-файл не был создан.",
            )
        return pdf_path.read_bytes()


async def export_docx(session: AsyncSession, user_id: UUID, document_id: UUID) -> tuple[bytes, str]:
    doc = await _load_owned_doc(session, user_id, document_id)
    path = _resolve_path(doc, "formatted_file_path", "docx")
    filename = f"{doc.title[:60]}.docx"
    return path.read_bytes(), filename


async def export_pdf(session: AsyncSession, user_id: UUID, document_id: UUID) -> tuple[bytes, str]:
    doc = await _load_owned_doc(session, user_id, document_id)
    path = _resolve_path(doc, "formatted_pdf_path", "pdf")
    filename = f"{doc.title[:60]}.pdf"
    return path.read_bytes(), filename


async def export_tex(session: AsyncSession, user_id: UUID, document_id: UUID) -> tuple[bytes, str]:
    doc = await _load_owned_doc(session, user_id, document_id)
    path = _resolve_path(doc, "formatted_tex_path", "tex")
    filename = f"{doc.title[:60]}.tex"
    return path.read_bytes(), filename
