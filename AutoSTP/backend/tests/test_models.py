"""Тесты ORM-моделей (схема БД по ER / DiplomaDatabase.drawio)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AISuggestion,
    AuditAction,
    AuditLog,
    BibliographicReference,
    Citation,
    Document,
    DocumentImage,
    DocumentTable,
    DocumentType,
    DocumentVersion,
    DocumentWorkflowStatus,
    Role,
    Section,
    Session,
    TableCell,
    Template,
    TemplateType,
    TextElement,
    User,
)


async def seed_roles(session: AsyncSession) -> tuple[Role, Role]:
    student = Role(title="student", description="Студент")
    admin = Role(title="admin", description="Администратор")
    session.add_all([student, admin])
    await session.flush()
    return student, admin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_role_and_user(db_session: AsyncSession) -> None:
    student_role, _ = await seed_roles(db_session)
    user = User(
        email="u1@example.com",
        password_hash="hash",
        full_name="Иван Иванов",
        role_id=student_role.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.password_hash == "hash"
    res = await db_session.execute(select(User).where(User.id == user.id).options(selectinload(User.role_obj)))
    loaded = res.scalar_one()
    assert loaded.role_obj.title == "student"


@pytest.mark.asyncio
async def test_document_version_current_pointer(db_session: AsyncSession) -> None:
    student_role, _ = await seed_roles(db_session)
    user = User(
        email="doc@example.com",
        password_hash="x",
        full_name="Doc User",
        role_id=student_role.id,
    )
    db_session.add(user)
    await db_session.flush()

    doc = Document(
        user_id=user.id,
        title="Курсовая",
        document_type=DocumentType.KU,
        status=DocumentWorkflowStatus.DRAFT,
        metadata_={"original_filename": "work.docx"},
    )
    db_session.add(doc)
    await db_session.flush()

    ver = DocumentVersion(
        document_id=doc.id,
        version_string="v1",
        snapshot={"nodes": []},
        content_hash="sha256:abc",
    )
    db_session.add(ver)
    await db_session.flush()

    doc.current_version_id = ver.id
    await db_session.commit()

    await db_session.refresh(doc)
    assert doc.current_version_id == ver.id
    assert doc.metadata_["original_filename"] == "work.docx"


@pytest.mark.asyncio
async def test_section_hierarchy_and_content(db_session: AsyncSession) -> None:
    student_role, _ = await seed_roles(db_session)
    user = User(email="s@e.com", password_hash="p", full_name="S", role_id=student_role.id)
    db_session.add(user)
    await db_session.flush()
    doc = Document(user_id=user.id, title="D", document_type=DocumentType.DI, status=DocumentWorkflowStatus.IN_PROGRESS)
    db_session.add(doc)
    await db_session.flush()

    intro = Section(
        document_id=doc.id,
        parent_id=None,
        section_type="introduction",
        title="Введение",
        order_number=0,
        level=1,
    )
    db_session.add(intro)
    await db_session.flush()

    sub = Section(
        document_id=doc.id,
        parent_id=intro.id,
        section_type="subsection",
        title="1.1 Постановка",
        order_number=0,
        level=2,
    )
    db_session.add(sub)
    await db_session.flush()

    te = TextElement(
        section_id=sub.id,
        element_type="paragraph",
        content="Текст абзаца",
        formatting={"bold": False},
        order_number=0,
    )
    db_session.add(te)
    await db_session.commit()

    r = await db_session.execute(
        select(Section).where(Section.id == intro.id).options(selectinload(Section.children))
    )
    root = r.scalar_one()
    assert len(root.children) == 1
    assert root.children[0].title.startswith("1.1")


@pytest.mark.asyncio
async def test_table_and_cells(db_session: AsyncSession) -> None:
    student_role, _ = await seed_roles(db_session)
    user = User(email="t@e.com", password_hash="p", full_name="T", role_id=student_role.id)
    db_session.add(user)
    await db_session.flush()
    doc = Document(user_id=user.id, title="D", document_type=DocumentType.KU, status=DocumentWorkflowStatus.DRAFT)
    db_session.add(doc)
    await db_session.flush()
    sec = Section(document_id=doc.id, section_type="body", title="Таблицы", order_number=0, level=1)
    db_session.add(sec)
    await db_session.flush()

    tbl = DocumentTable(
        section_id=sec.id,
        caption="Таблица 1",
        table_number=1,
        order_number=0,
        rows_number=2,
        columns_number=2,
    )
    db_session.add(tbl)
    await db_session.flush()

    db_session.add_all(
        [
            TableCell(table_id=tbl.id, is_header=True, row_index=0, column_index=0, content="A"),
            TableCell(table_id=tbl.id, is_header=True, row_index=0, column_index=1, content="B"),
            TableCell(table_id=tbl.id, is_header=False, row_index=1, column_index=0, content="1"),
            TableCell(table_id=tbl.id, is_header=False, row_index=1, column_index=1, content="2"),
        ]
    )
    await db_session.commit()

    q = await db_session.execute(select(DocumentTable).where(DocumentTable.id == tbl.id).options(selectinload(DocumentTable.cells)))
    loaded = q.scalar_one()
    assert len(loaded.cells) == 4
    assert loaded.rows_number == 2


@pytest.mark.asyncio
async def test_image_ai_suggestion(db_session: AsyncSession) -> None:
    student_role, _ = await seed_roles(db_session)
    user = User(email="i@e.com", password_hash="p", full_name="I", role_id=student_role.id)
    db_session.add(user)
    await db_session.flush()
    doc = Document(user_id=user.id, title="D", document_type=DocumentType.KU, status=DocumentWorkflowStatus.DRAFT)
    db_session.add(doc)
    await db_session.flush()
    sec = Section(document_id=doc.id, section_type="body", title="Рисунки", order_number=0, level=1)
    db_session.add(sec)
    await db_session.flush()

    img = DocumentImage(
        section_id=sec.id,
        file_bytes=b"\x89PNG\r\n",
        caption="Рис. 1",
        alt="Схема",
        image_number=1,
        order_number=0,
    )
    sug = AISuggestion(section_id=sec.id, suggestion_text="Добавьте вывод по разделу", accepted=None)
    db_session.add_all([img, sug])
    await db_session.commit()

    await db_session.refresh(sug)
    assert sug.suggestion_text.startswith("Добавьте")


@pytest.mark.asyncio
async def test_bibliography_and_citation(db_session: AsyncSession) -> None:
    student_role, _ = await seed_roles(db_session)
    user = User(email="b@e.com", password_hash="p", full_name="B", role_id=student_role.id)
    db_session.add(user)
    await db_session.flush()
    doc = Document(user_id=user.id, title="D", document_type=DocumentType.KU, status=DocumentWorkflowStatus.DRAFT)
    db_session.add(doc)
    await db_session.flush()
    sec = Section(document_id=doc.id, section_type="body", title="Основная часть", order_number=0, level=1)
    db_session.add(sec)
    await db_session.flush()
    te = TextElement(section_id=sec.id, element_type="paragraph", content="Согласно [1]", order_number=0)
    db_session.add(te)
    await db_session.flush()

    ref = BibliographicReference(
        document_id=doc.id,
        reference_num=1,
        source_title="Информатика",
        authors="Иванов И.И.",
        source_type="book",
        source_link=None,
        order_number=0,
    )
    db_session.add(ref)
    await db_session.flush()

    cit = Citation(
        text_element_id=te.id,
        bibliographic_reference_id=ref.id,
        content="[1]",
    )
    db_session.add(cit)
    await db_session.commit()

    rq = await db_session.execute(
        select(Citation).where(Citation.id == cit.id).options(
            selectinload(Citation.text_element),
            selectinload(Citation.bibliographic_reference),
        )
    )
    c = rq.scalar_one()
    assert c.bibliographic_reference.source_title == "Информатика"


@pytest.mark.asyncio
async def test_template_session_audit(db_session: AsyncSession) -> None:
    student_role, admin_role = await seed_roles(db_session)
    user = User(email="a@e.com", password_hash="p", full_name="A", role_id=student_role.id)
    db_session.add(user)
    await db_session.flush()

    template = Template(
        user_id=user.id,
        type=TemplateType.PERSONAL,
        name="Мой шаблон",
        template_json={"font": "Times New Roman"},
    )
    sess = Session(
        user_id=user.id,
        refresh_token="rtoken",
        expires_at=utc_now() + timedelta(days=7),
    )
    log = AuditLog(
        user_id=user.id,
        action=AuditAction.LOGIN,
        log_msg="Успешный вход",
        details={"ip": "127.0.0.1"},
        ip_address="127.0.0.1",
    )
    db_session.add_all([template, sess, log])
    await db_session.commit()

    await db_session.refresh(log)
    assert log.log_msg == "Успешный вход"
    assert admin_role.title == "admin"


@pytest.mark.asyncio
async def test_cascade_delete_document(db_session: AsyncSession) -> None:
    student_role, _ = await seed_roles(db_session)
    user = User(email="c@e.com", password_hash="p", full_name="C", role_id=student_role.id)
    db_session.add(user)
    await db_session.flush()
    doc = Document(user_id=user.id, title="Temp", document_type=DocumentType.KU, status=DocumentWorkflowStatus.DRAFT)
    db_session.add(doc)
    await db_session.flush()
    sec = Section(document_id=doc.id, section_type="body", title="X", order_number=0, level=1)
    db_session.add(sec)
    await db_session.flush()
    te = TextElement(section_id=sec.id, element_type="p", content="x", order_number=0)
    db_session.add(te)
    await db_session.flush()
    ref = BibliographicReference(document_id=doc.id, reference_num=1, order_number=0)
    db_session.add(ref)
    await db_session.flush()

    await db_session.delete(doc)
    await db_session.commit()

    assert (await db_session.execute(select(Section).where(Section.id == sec.id))).scalar_one_or_none() is None
    assert (await db_session.execute(select(TextElement).where(TextElement.id == te.id))).scalar_one_or_none() is None
