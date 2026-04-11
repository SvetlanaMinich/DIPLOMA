"""Структура документа: разделы, текст, таблицы, изображения, ИИ, библиография (DB3–DB5)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Section(Base):
    """Раздел документа (возможна иерархия через parent_id)."""

    __tablename__ = "sections"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    section_type: Mapped[str] = mapped_column(String(64), nullable=False, default="body")
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    order_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    document: Mapped[Document] = relationship("Document", back_populates="sections")
    parent: Mapped[Section | None] = relationship(
        "Section",
        remote_side="Section.id",
        back_populates="children",
    )
    children: Mapped[list[Section]] = relationship(
        "Section",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    text_elements: Mapped[list[TextElement]] = relationship(
        "TextElement",
        back_populates="section",
        cascade="all, delete-orphan",
    )
    tables: Mapped[list[DocumentTable]] = relationship(
        "DocumentTable",
        back_populates="section",
        cascade="all, delete-orphan",
    )
    images: Mapped[list[DocumentImage]] = relationship(
        "DocumentImage",
        back_populates="section",
        cascade="all, delete-orphan",
    )
    ai_suggestions: Mapped[list[AISuggestion]] = relationship(
        "AISuggestion",
        back_populates="section",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Section(id={self.id}, title='{self.title[:30]}...')>"


class TextElement(Base):
    """Текстовый фрагмент внутри раздела (абзац, заголовок и т.д.)."""

    __tablename__ = "text_elements"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    section_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    element_type: Mapped[str] = mapped_column(String(64), nullable=False, default="paragraph")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    formatting: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    order_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    section: Mapped[Section] = relationship("Section", back_populates="text_elements")
    citations: Mapped[list[Citation]] = relationship(
        "Citation",
        back_populates="text_element",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TextElement(id={self.id}, element_type='{self.element_type}')>"


class DocumentTable(Base):
    """Таблица в разделе (имя класса не `Table`, чтобы не конфликтовать с SQLAlchemy)."""

    __tablename__ = "document_tables"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    section_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    caption: Mapped[str | None] = mapped_column(String(512), nullable=True)
    table_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    columns_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    section: Mapped[Section] = relationship("Section", back_populates="tables")
    cells: Mapped[list[TableCell]] = relationship(
        "TableCell",
        back_populates="table",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DocumentTable(id={self.id}, rows={self.rows_number}, cols={self.columns_number})>"


class TableCell(Base):
    """Ячейка таблицы."""

    __tablename__ = "table_cells"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    table_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document_tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_header: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")

    table: Mapped[DocumentTable] = relationship("DocumentTable", back_populates="cells")

    def __repr__(self) -> str:
        return f"<TableCell(r={self.row_index}, c={self.column_index})>"


class DocumentImage(Base):
    """Изображение в разделе (байты файла по схеме draw.io)."""

    __tablename__ = "document_images"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    section_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    caption: Mapped[str | None] = mapped_column(String(512), nullable=True)
    alt: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    section: Mapped[Section] = relationship("Section", back_populates="images")

    def __repr__(self) -> str:
        return f"<DocumentImage(id={self.id})>"


class AISuggestion(Base):
    """Подсказка ИИ по разделу (DB5)."""

    __tablename__ = "ai_suggestions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    section_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    section: Mapped[Section] = relationship("Section", back_populates="ai_suggestions")

    def __repr__(self) -> str:
        return f"<AISuggestion(id={self.id})>"


class BibliographicReference(Base):
    """Элемент списка источников документа."""

    __tablename__ = "bibliographic_references"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_link: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    order_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    document: Mapped[Document] = relationship("Document", back_populates="bibliographic_references")
    citations: Mapped[list[Citation]] = relationship(
        "Citation",
        back_populates="bibliographic_reference",
    )

    def __repr__(self) -> str:
        return f"<BibliographicReference(id={self.id}, ref_num={self.reference_num})>"


class Citation(Base):
    """Связь фрагмента текста с библиографической записью."""

    __tablename__ = "citations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    text_element_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("text_elements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bibliographic_reference_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bibliographic_references.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    text_element: Mapped[TextElement] = relationship("TextElement", back_populates="citations")
    bibliographic_reference: Mapped[BibliographicReference] = relationship(
        "BibliographicReference",
        back_populates="citations",
    )

    def __repr__(self) -> str:
        return f"<Citation(id={self.id})>"


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.document import Document
