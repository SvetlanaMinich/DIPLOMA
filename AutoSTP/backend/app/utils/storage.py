"""Сохранение загруженных файлов на диск."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from uuid import UUID

from app.core.config import settings


def _upload_root() -> Path:
    return Path(settings.UPLOAD_DIR).resolve()


def safe_original_filename(name: str | None) -> str:
    if not name or not name.strip():
        return "upload.bin"
    base = Path(name).name
    base = re.sub(r"[^\w.\-]", "_", base, flags=re.UNICODE)
    if not base or base in {".", ".."}:
        return "upload.bin"
    return base[:255]


def document_storage_dir(user_id: UUID, document_id: UUID) -> Path:
    return _upload_root() / str(user_id) / str(document_id)


def save_original_file(user_id: UUID, document_id: UUID, filename: str, data: bytes) -> tuple[str, str]:
    """
    Пишет файл в UPLOAD_DIR/<user_id>/<document_id>/<safe_name>.

    Returns:
        (relative_dir, stored_filename) — relative_dir относительно UPLOAD_DIR.
    """
    d = document_storage_dir(user_id, document_id)
    d.mkdir(parents=True, exist_ok=True)
    stored = safe_original_filename(filename)
    path = d / stored
    path.write_bytes(data)
    rel = f"{user_id}/{document_id}"
    return rel, stored


def delete_document_storage(user_id: UUID, document_id: UUID) -> None:
    d = document_storage_dir(user_id, document_id)
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)
