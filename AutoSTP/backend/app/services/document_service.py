from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.document import Document, DocumentType, DocumentVersion, DocumentWorkflowStatus
from app.models.user import User
from app.schemas.document import (
    DocumentDetail,
    DocumentListItem,
    DocumentListResponse,
    DocumentUpdate,
    DocumentVersionOut,
)
from app.utils import doc_text, storage


def _title_from_filename(name: str) -> str:
    from pathlib import Path

    stem = Path(name).stem
    return stem if stem else "Документ"


def _max_bytes() -> int:
    return settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


async def read_upload_with_limit(file: UploadFile) -> tuple[bytes, str]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя файла не указано",
        )
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Допустимые форматы: {', '.join(settings.ALLOWED_FILE_EXTENSIONS)}",
        )
    chunks: list[bytes] = []
    total = 0
    max_b = _max_bytes()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_b:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Файл больше {settings.MAX_UPLOAD_SIZE_MB} МБ",
            )
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пустой файл",
        )
    return data, ext


def _plain_text_for_upload(data: bytes, ext: str) -> str:
    if ext == ".docx":
        return doc_text.extract_text_from_docx(data)
    return doc_text.extract_text_from_txt(data)


def _filename_stored_as_docx(original_filename: str) -> str:
    """Имя файла на диске всегда с расширением .docx."""
    from pathlib import Path

    base = Path(original_filename).name
    stem = Path(base).stem if base else "document"
    if not stem or stem in {".", ".."}:
        stem = "document"
    return storage.safe_original_filename(f"{stem}.docx")


def _snapshot_hash(snapshot: dict) -> str:
    payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


async def create_document_from_upload(
    session: AsyncSession,
    user: User,
    *,
    file: UploadFile,
    title: str | None,
    document_type: DocumentType,
) -> Document:
    data, ext = await read_upload_with_limit(file)
    plain = _plain_text_for_upload(data, ext)

    doc_id = uuid4()
    ver_id = uuid4()
    safe_name = file.filename or "upload.bin"
    display_title = (title or "").strip() or _title_from_filename(safe_name)

    if ext == ".txt":
        file_bytes = doc_text.plain_text_to_docx_bytes(plain)
    else:
        file_bytes = data

    storage_filename = _filename_stored_as_docx(safe_name)

    snapshot = {
        "plain_text": plain,
        "nodes": [],
        "source_format": ext.lstrip("."),
        "stored_file_format": "docx",
    }
    meta = {
        "original_filename": safe_name,
        "upload_extension": ext,
        "stored_filename": storage_filename,
        "stored_file_format": "docx",
        "storage_dir": f"{user.id}/{doc_id}",
    }

    doc = Document(
        id=doc_id,
        user_id=user.id,
        title=display_title[:512],
        document_type=document_type,
        status=DocumentWorkflowStatus.DRAFT,
        metadata_=meta,
        current_version_id=None,
    )
    ver = DocumentVersion(
        id=ver_id,
        document_id=doc_id,
        version_string="v1",
        snapshot=snapshot,
        content_hash=_snapshot_hash(snapshot),
    )
    session.add(doc)
    session.add(ver)
    try:
        await session.flush()
        rel, stored = storage.save_original_file(user.id, doc_id, storage_filename, file_bytes)
        meta["storage_relpath"] = rel
        meta["stored_filename"] = stored
        doc.current_version_id = ver_id
        await session.commit()
    except Exception:
        await session.rollback()
        storage.delete_document_storage(user.id, doc_id)
        raise

    res = await session.execute(
        select(Document)
        .where(Document.id == doc_id)
        .options(
            selectinload(Document.current_version),
            selectinload(Document.versions),
        )
    )
    return res.scalar_one()


async def get_owned_document(session: AsyncSession, user_id: UUID, document_id: UUID) -> Document:
    res = await session.execute(
        select(Document)
        .where(Document.id == document_id, Document.user_id == user_id)
        .options(
            selectinload(Document.current_version),
            selectinload(Document.versions),
        )
    )
    doc = res.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )
    return doc


def document_to_detail(doc: Document) -> DocumentDetail:
    cv = doc.current_version
    current_out = None
    if cv is not None:
        current_out = DocumentVersionOut(
            id=str(cv.id),
            version_string=cv.version_string,
            created_at=cv.created_at,
            snapshot=cv.snapshot,
        )
    meta = doc.metadata_
    return DocumentDetail(
        id=str(doc.id),
        title=doc.title,
        document_type=doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type),
        status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        metadata=meta,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        current_version=current_out,
        versions_count=len(doc.versions) if doc.versions is not None else 0,
    )


def document_to_list_item(doc: Document) -> DocumentListItem:
    meta = doc.metadata_
    orig = None
    if isinstance(meta, dict):
        orig = meta.get("original_filename")
    return DocumentListItem(
        id=str(doc.id),
        title=doc.title,
        document_type=doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type),
        status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        original_filename=orig,
    )


async def list_user_documents(
    session: AsyncSession,
    user_id: UUID,
    *,
    skip: int,
    limit: int,
    title_contains: str | None,
) -> DocumentListResponse:
    filters: list[Any] = [Document.user_id == user_id]
    if title_contains and title_contains.strip():
        filters.append(Document.title.ilike(f"%{title_contains.strip()}%"))
    count_stmt = select(func.count()).select_from(Document).where(*filters)
    total_res = await session.execute(count_stmt)
    total = int(total_res.scalar_one() or 0)

    stmt = (
        select(Document)
        .where(*filters)
        .order_by(Document.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await session.execute(stmt)
    rows = res.scalars().all()
    return DocumentListResponse(
        items=[document_to_list_item(d) for d in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


async def update_document_content(
    session: AsyncSession,
    user: User,
    document_id: UUID,
    body: DocumentUpdate,
) -> DocumentDetail:
    doc = await get_owned_document(session, user.id, document_id)
    if body.title is not None:
        doc.title = body.title.strip()[:512]
    cnt_res = await session.execute(
        select(func.count()).select_from(DocumentVersion).where(DocumentVersion.document_id == doc.id)
    )
    n = int(cnt_res.scalar_one() or 0)
    ver_id = uuid4()
    snap = body.snapshot
    ver = DocumentVersion(
        id=ver_id,
        document_id=doc.id,
        version_string=f"v{n + 1}",
        snapshot=snap,
        content_hash=_snapshot_hash(snap),
    )
    session.add(ver)
    await session.flush()
    doc.current_version_id = ver_id
    doc_pk = doc.id
    await session.commit()
    session.expire_all()
    res = await session.execute(
        select(Document)
        .where(Document.id == doc_pk)
        .options(selectinload(Document.current_version), selectinload(Document.versions))
    )
    fresh = res.scalar_one()
    return document_to_detail(fresh)


async def delete_document(session: AsyncSession, user: User, document_id: UUID) -> None:
    doc = await get_owned_document(session, user.id, document_id)
    uid, did = doc.user_id, doc.id
    await session.delete(doc)
    await session.commit()
    storage.delete_document_storage(uid, did)
