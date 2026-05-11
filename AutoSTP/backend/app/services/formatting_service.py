"""Format a segmented document using LaTeX templates per STP 01-2024."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentWorkflowStatus
from app.models.document_content import Section
from app.models.template import Template
from app.schemas.document import DocumentDetail
from app.schemas.template import TemplateConfiguration
from app.services import document_service
from app.services.latex_service import (
    _UNNUMBERED_ROLES,
    build_template_context,
    compile_latex_to_pdf,
    convert_latex_to_docx,
    render_latex,
)
from app.utils import storage

logger = logging.getLogger(__name__)


def build_docx(sections: list[Section], cfg: TemplateConfiguration) -> bytes:
    ctx = build_template_context(sections=sections, cfg=cfg, references=[], document_title="")
    tex_source = render_latex(ctx)
    return convert_latex_to_docx(tex_source)


async def format_document(
    session: AsyncSession,
    user_id: UUID,
    document_id: UUID,
    template_id: UUID,
) -> DocumentDetail:
    doc_res = await session.execute(
        select(Document)
        .where(Document.id == document_id, Document.user_id == user_id)
        .options(
            selectinload(Document.current_version),
            selectinload(Document.versions),
            selectinload(Document.sections)
            .selectinload(Section.text_elements),
        )
    )
    doc = doc_res.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not doc.sections:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Документ не сегментирован. Сначала выполните сегментацию.",
        )

    tmpl_res = await session.execute(select(Template).where(Template.id == template_id))
    tmpl = tmpl_res.scalar_one_or_none()
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")

    try:
        cfg = TemplateConfiguration.model_validate(tmpl.template_json)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Не удалось разобрать шаблон: {exc}",
        ) from exc

    logger.info("Formatting document %s with template %s via LaTeX", document_id, template_id)

    ctx = build_template_context(
        sections=doc.sections,
        cfg=cfg,
        references=list(doc.bibliographic_references) if doc.bibliographic_references else [],
        document_title=doc.title or "",
    )
    tex_source = render_latex(ctx)

    pdf_bytes = compile_latex_to_pdf(tex_source)
    docx_bytes = convert_latex_to_docx(tex_source)

    _, _pdf_stored = storage.save_original_file(
        doc.user_id, doc.id, "formatted.pdf", pdf_bytes
    )
    _rel_docx, _docx_stored = storage.save_original_file(
        doc.user_id, doc.id, "formatted.docx", docx_bytes
    )

    tex_path = storage.document_storage_dir(doc.user_id, doc.id) / "source.tex"
    tex_path.write_text(tex_source, encoding="utf-8")

    meta = dict(doc.metadata_ or {})
    meta["formatted_file_path"] = f"{doc.user_id}/{doc.id}/formatted.docx"
    meta["formatted_pdf_path"] = f"{doc.user_id}/{doc.id}/formatted.pdf"
    meta["formatted_tex_path"] = f"{doc.user_id}/{doc.id}/source.tex"
    meta["formatted_template_id"] = str(template_id)
    doc.metadata_ = meta
    doc.status = DocumentWorkflowStatus.FORMATTED
    await session.commit()

    res = await session.execute(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.current_version), selectinload(Document.versions))
    )
    fresh = res.scalar_one()
    return document_service.document_to_detail(fresh)
