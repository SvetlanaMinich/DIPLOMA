"""CRUD и загрузка документов."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_async_session
from app.core.limiter import limiter
from app.models.audit import AuditAction
from app.models.document import DocumentType
from app.models.user import User
from app.schemas.document import DocumentDetail, DocumentListResponse, DocumentUpdate, FormatRequest
from app.schemas.hints import HintsResponse
from app.schemas.segmentation import SegmentRequest, SegmentResponse
from app.services import document_service, formatting_service, hints_service, segmentation_service, export_service
from app.utils.audit import write_audit_log

router = APIRouter()


def _parse_document_type(raw: str) -> DocumentType:
    try:
        return DocumentType(raw.lower().strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_type: допустимы ku или di",
        )


@router.post("/upload", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    document_type: str = Form("ku"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> DocumentDetail:
    dtype = _parse_document_type(document_type)
    doc = await document_service.create_document_from_upload(
        session, user, file=file, title=title, document_type=dtype
    )
    await write_audit_log(
        session, user_id=user.id, action=AuditAction.DOCUMENT_UPLOAD,
        log_msg=f"Загружен документ: {doc.title}",
        details={"document_id": str(doc.id)},
    )
    await session.commit()
    return document_service.document_to_detail(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    title_contains: str | None = Query(None, max_length=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> DocumentListResponse:
    return await document_service.list_user_documents(
        session,
        user.id,
        skip=skip,
        limit=limit,
        title_contains=title_contains,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> DocumentDetail:
    doc = await document_service.get_owned_document(session, user.id, document_id)
    return document_service.document_to_detail(doc)


@router.put("/{document_id}", response_model=DocumentDetail)
async def update_document(
    document_id: UUID,
    body: DocumentUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> DocumentDetail:
    return await document_service.update_document_content(session, user, document_id, body)


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    await document_service.delete_document(session, user, document_id)
    await write_audit_log(
        session, user_id=user.id, action=AuditAction.DOCUMENT_DELETE,
        details={"document_id": str(document_id)},
    )
    await session.commit()
    return {"detail": "deleted"}


@router.post("/{document_id}/segment", response_model=SegmentResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def segment_document(
    request: Request,
    document_id: UUID,
    body: SegmentRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> SegmentResponse:
    result = await segmentation_service.segment_document(
        session, user.id, document_id, body.template_id
    )
    await write_audit_log(
        session, user_id=user.id, action=AuditAction.DOCUMENT_SEGMENT,
        details={"document_id": str(document_id), "sections": result.total_sections},
    )
    await session.commit()
    return result


@router.post("/{document_id}/format", response_model=DocumentDetail, status_code=status.HTTP_200_OK)
async def format_document(
    document_id: UUID,
    body: FormatRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> DocumentDetail:
    from uuid import UUID as _UUID
    detail = await formatting_service.format_document(
        session, user.id, document_id, _UUID(body.template_id)
    )
    await write_audit_log(
        session, user_id=user.id, action=AuditAction.DOCUMENT_FORMAT,
        details={"document_id": str(document_id), "template_id": body.template_id},
    )
    await session.commit()
    return detail


@router.get("/{document_id}/export/docx")
async def export_docx(
    document_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    docx_bytes, filename = await export_service.export_docx(session, user.id, document_id)
    await write_audit_log(
        session, user_id=user.id, action=AuditAction.DOCUMENT_EXPORT,
        details={"document_id": str(document_id), "format": "docx"},
    )
    await session.commit()
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{document_id}/export/pdf")
async def export_pdf(
    document_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    pdf_bytes, filename = await export_service.export_pdf(session, user.id, document_id)
    await write_audit_log(
        session, user_id=user.id, action=AuditAction.DOCUMENT_EXPORT,
        details={"document_id": str(document_id), "format": "pdf"},
    )
    await session.commit()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{document_id}/export/tex")
async def export_tex(
    document_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    tex_bytes, filename = await export_service.export_tex(session, user.id, document_id)
    await write_audit_log(
        session, user_id=user.id, action=AuditAction.DOCUMENT_EXPORT,
        details={"document_id": str(document_id), "format": "tex"},
    )
    await session.commit()
    return Response(
        content=tex_bytes,
        media_type="text/x-tex",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{document_id}/sections/{section_id}/hints",
    response_model=HintsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_section_hints(
    document_id: UUID,
    section_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> HintsResponse:
    hints = await hints_service.generate_hints(session, user.id, document_id, section_id)
    return HintsResponse(section_id=str(section_id), hints=hints)
