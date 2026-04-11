"""Document and version models (DB2)."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentType(str, PyEnum):
    """Тип работы: курсовая (ku) / диплом (di)."""

    KU = "ku"
    DI = "di"


class DocumentWorkflowStatus(str, PyEnum):
    """Статус жизненного цикла документа в редакторе."""

    DRAFT = "draft"
    IN_PROGRESS = "inpr"
    COMPLETED = "com"


class Document(Base):
    """Корневая сущность документа пользователя."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    current_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "document_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_documents_current_version_id",
        ),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        String(16),
        default=DocumentType.KU,
        nullable=False,
    )
    status: Mapped[DocumentWorkflowStatus] = mapped_column(
        String(16),
        default=DocumentWorkflowStatus.DRAFT,
        nullable=False,
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="documents")
    versions: Mapped[list[DocumentVersion]] = relationship(
        "DocumentVersion",
        back_populates="document",
        foreign_keys="DocumentVersion.document_id",
        cascade="all, delete-orphan",
    )
    current_version: Mapped[DocumentVersion | None] = relationship(
        "DocumentVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )
    sections: Mapped[list[Section]] = relationship(
        "Section",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    bibliographic_references: Mapped[list[BibliographicReference]] = relationship(
        "BibliographicReference",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}')>"


class DocumentVersion(Base):
    """Версия содержимого документа (снимок JSON + строка версии)."""

    __tablename__ = "document_versions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_string: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    document: Mapped[Document] = relationship(
        "Document",
        back_populates="versions",
        foreign_keys=[document_id],
    )

    def __repr__(self) -> str:
        return f"<DocumentVersion(id={self.id}, version_string='{self.version_string}')>"


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.document_content import BibliographicReference, Section
    from app.models.user import User
