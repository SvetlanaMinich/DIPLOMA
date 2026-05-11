"""Live end-to-end tests — require a real OPENROUTER_API_KEY and test DB.

These tests call OpenRouter for real. They are skipped unless the env var is
set, so CI stays fast. Run manually:

    OPENROUTER_API_KEY=sk-... pytest -m live tests/test_live.py -v -s

Or, if the key is already in .env:

    pytest -m live tests/test_live.py -v -s
"""
from __future__ import annotations

import os
import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import register_and_login_headers
from tests.test_segmentation import SAMPLE_TEXT, WORK_STRUCTURE_JSON

pytestmark = pytest.mark.live

# ---------------------------------------------------------------------------
# Skip all tests in this module if OPENROUTER_API_KEY is absent
# ---------------------------------------------------------------------------

_SKIP = not os.getenv("OPENROUTER_API_KEY")
skip_no_key = pytest.mark.skipif(_SKIP, reason="OPENROUTER_API_KEY not set")


# ---------------------------------------------------------------------------
# Minimal template JSON for format/export stages
# ---------------------------------------------------------------------------

_TEMPLATE_JSON = {
    "work_structure": WORK_STRUCTURE_JSON,
    "page": {
        "margin_left_mm": 30.0,
        "margin_right_mm": 15.0,
        "margin_top_mm": 20.0,
        "margin_bottom_mm": 20.0,
        "page_number_pos": "bottom_right",
    },
    "fonts": {
        "main_family": "Times New Roman",
        "main_size_pt": 14.0,
        "line_height_pt": 18.0,
        "paragraph_indent_mm": 12.5,
        "text_alignment": "justify",
    },
    "headers": {
        "unnumbered_alignment": "center",
        "numbered_alignment": "left",
        "level_1": {"bold": True, "uppercase": True, "new_page": True},
    },
}

_KNOWN_ROLES = {
    "title_page", "abstract", "task", "contents", "abbreviations",
    "introduction", "main_body", "conclusion", "references",
    "appendices", "document_list", "safety_ecology", "tech_economy",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _upload_doc(client: AsyncClient, headers: dict, text: str = SAMPLE_TEXT) -> str:
    files = {"file": ("document.txt", text.encode(), "text/plain")}
    resp = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_template(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/templates/",
        json={"name": "Live Test Template", "type": "personal", "template_json": _TEMPLATE_JSON},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Test 1: OpenRouter connectivity
# ---------------------------------------------------------------------------

@skip_no_key
@pytest.mark.asyncio
async def test_live_openrouter_ping(client: AsyncClient, db_session: AsyncSession) -> None:
    """Verify the API key is valid and the model responds at all."""
    from app.services.openrouter_service import ping_model
    result = await ping_model()
    assert isinstance(result, str)
    assert len(result) > 0, "ping_model returned empty string"


# ---------------------------------------------------------------------------
# Test 2: Segmentation — LLM returns sensible sections
# ---------------------------------------------------------------------------

@skip_no_key
@pytest.mark.asyncio
async def test_live_segmentation_returns_sections(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Real LLM call: upload document, segment it, check sections are found."""
    headers = await register_and_login_headers(client, email="live_seg@example.com")
    doc_id = await _upload_doc(client, headers)
    tmpl_id = await _create_template(client, headers)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/segment",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    sections = body["sections"]
    assert len(sections) >= 1, "LLM returned zero sections"

    roles = {s["role"] for s in sections}
    assert roles <= _KNOWN_ROLES, f"Unknown roles returned: {roles - _KNOWN_ROLES}"

    # Sample text has clear ВВЕДЕНИЕ and ЗАКЛЮЧЕНИЕ — LLM must find at least one
    expected = {"introduction", "conclusion", "references", "main_body"}
    found = roles & expected
    assert len(found) >= 1, (
        f"LLM found none of {expected}; got roles={roles}. "
        "Check the model output — segmentation prompt may need tuning."
    )


@skip_no_key
@pytest.mark.asyncio
async def test_live_segmentation_section_text_non_empty(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Each section returned by real LLM must have a non-empty title."""
    headers = await register_and_login_headers(client, email="live_seg2@example.com")
    doc_id = await _upload_doc(client, headers)
    tmpl_id = await _create_template(client, headers)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/segment",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    for sec in resp.json()["sections"]:
        assert sec["title"], f"Section with role={sec['section_type']} has empty title"


# ---------------------------------------------------------------------------
# Test 3: Hints — LLM returns recommendations
# ---------------------------------------------------------------------------

@skip_no_key
@pytest.mark.asyncio
async def test_live_hints_returns_list(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Real LLM call: segment doc, request hints for first section."""
    headers = await register_and_login_headers(client, email="live_hints@example.com")
    doc_id = await _upload_doc(client, headers)
    tmpl_id = await _create_template(client, headers)

    seg_resp = await client.post(
        f"/api/v1/documents/{doc_id}/segment",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert seg_resp.status_code == 200, seg_resp.text
    sections = seg_resp.json()["sections"]
    assert sections, "No sections from segmentation — cannot test hints"

    section_id = sections[0]["id"]
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/sections/{section_id}/hints",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert "hints" in body
    assert isinstance(body["hints"], list)
    assert len(body["hints"]) >= 1, "LLM returned zero hints"
    for hint in body["hints"]:
        assert isinstance(hint, str) and hint.strip(), "Hint is not a non-empty string"


# ---------------------------------------------------------------------------
# Test 4: Full pipeline — upload → segment → format → export DOCX
# ---------------------------------------------------------------------------

@skip_no_key
@pytest.mark.asyncio
async def test_live_full_pipeline_docx_export(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    """End-to-end: real segmentation, then format, then download DOCX."""
    headers = await register_and_login_headers(client, email="live_pipeline@example.com")
    doc_id = await _upload_doc(client, headers)
    tmpl_id = await _create_template(client, headers)

    # Segment
    seg = await client.post(
        f"/api/v1/documents/{doc_id}/segment",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert seg.status_code == 200, f"Segmentation failed: {seg.text}"
    assert len(seg.json()["sections"]) >= 1

    # Format
    fmt = await client.post(
        f"/api/v1/documents/{doc_id}/format",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert fmt.status_code == 200, f"Format failed: {fmt.text}"
    assert fmt.json()["status"] == "formatted"

    # Export DOCX
    export = await client.get(
        f"/api/v1/documents/{doc_id}/export/docx",
        headers=headers,
    )
    assert export.status_code == 200, f"Export failed: {export.text}"
    assert export.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    docx_bytes = export.content
    assert len(docx_bytes) > 1_000, "DOCX file is suspiciously small"

    # Verify it's a real DOCX (ZIP-based)
    assert docx_bytes[:2] == b"PK", "DOCX must start with PK (ZIP magic bytes)"


# ---------------------------------------------------------------------------
# Test 5: Template extraction — LLM fills unified JSON from a standard document
# ---------------------------------------------------------------------------

# Minimal excerpt from an academic standard — enough for the LLM to extract rules
_STP_EXCERPT = """\
2 ТРЕБОВАНИЯ К ПОЯСНИТЕЛЬНОЙ ЗАПИСКЕ

2.1 Общие требования к оформлению

Пояснительную записку выполняют на листах формата А4 (210×297 мм).
Поля: левое – 30 мм, правое – 15 мм, верхнее – 20 мм, нижнее – 20 мм.
Нумерация страниц – арабскими цифрами в правом нижнем углу листа.
Первая страница (титульный лист) включается в общую нумерацию, но номер на ней не ставится.
Шрифт основного текста – Times New Roman, размер 14 пт.
Межстрочный интервал – 18 пт (полуторный).
Абзацный отступ – 12,5 мм от левого поля.
Текст выравнивается по ширине страницы.
Переносы в тексте допускаются.
В заголовках переносы не допускаются.

2.2 Заголовки разделов и подразделов

Заголовки разделов пишут прописными буквами, полужирным шрифтом, по центру страницы.
Каждый раздел начинается с новой страницы.
Заголовки подразделов пишут строчными буквами (кроме первой), полужирным шрифтом, по левому краю.
Точка в конце заголовков не ставится.
Заголовки не подчёркиваются.
Абзацный отступ для заголовков не применяется.

2.3 Перечисления

При простом перечислении используют тире (–) в начале каждого элемента.
После каждого элемента простого перечня ставят точку с запятой, после последнего – точку.
При буквенном перечне: а), б), в) – строчные буквы со скобкой.
При цифровом перечне: 1), 2), 3).

2.4 Формулы

Формулы располагают посередине строки.
Нумерацию формул дают в скобках у правого края в пределах раздела: (1.1), (1.2).
После формулы с новой строки пишут слово «где» без двоеточия и поясняют обозначения.
Формулы отделяют от основного текста пустыми строками сверху и снизу.

2.5 Иллюстрации

Иллюстрации располагают по центру страницы после первой ссылки на них в тексте.
Подрисуночная подпись размещается под рисунком по центру.
Пример подписи: Рисунок 1.1 – Структура системы.
Нумерация рисунков – в пределах раздела.

2.6 Таблицы

Заголовок таблицы располагается слева над таблицей.
Пример: Таблица 1.1 – Основные параметры системы.
Нумерация таблиц – в пределах раздела.
При переносе таблицы на следующую страницу пишут «Продолжение таблицы 1.1».
Заголовки граф таблицы пишут с прописной буквы.

2.7 Список использованных источников

Заголовок СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ пишется прописными буквами по центру.
Список оформляется в соответствии с ГОСТ 7.1–2003.
Ссылки в тексте – в квадратных скобках с порядковым номером: [1].
Источники располагают в порядке упоминания в тексте.
"""


@skip_no_key
@pytest.mark.asyncio
async def test_live_extract_only_returns_config(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """extract-only: LLM reads a standard text and returns a filled TemplateConfiguration."""
    headers = await register_and_login_headers(client, email="live_ext1@example.com")

    files = {"file": ("stp_excerpt.txt", _STP_EXCERPT.encode("utf-8"), "text/plain")}
    resp = await client.post(
        "/api/v1/templates/extract-only",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    cfg = resp.json()

    # Page margins must be extracted from the explicit "30 мм / 15 мм / 20 мм / 20 мм" values
    page = cfg.get("page") or {}
    assert page.get("margin_left_mm") == 30.0, f"margin_left_mm: {page.get('margin_left_mm')}"
    assert page.get("margin_right_mm") == 15.0, f"margin_right_mm: {page.get('margin_right_mm')}"
    assert page.get("margin_top_mm") == 20.0, f"margin_top_mm: {page.get('margin_top_mm')}"
    assert page.get("margin_bottom_mm") == 20.0, f"margin_bottom_mm: {page.get('margin_bottom_mm')}"
    assert page.get("page_number_pos") is not None

    # Font rules
    fonts = cfg.get("fonts") or {}
    assert fonts.get("main_family") is not None, "main_family not extracted"
    assert fonts.get("main_size_pt") == 14.0, f"main_size_pt: {fonts.get('main_size_pt')}"
    assert fonts.get("paragraph_indent_mm") == 12.5, f"indent: {fonts.get('paragraph_indent_mm')}"

    # Heading rules
    headers_cfg = cfg.get("headers") or {}
    h1 = headers_cfg.get("level_1") or {}
    assert h1.get("uppercase") is True, "level_1 must be uppercase"
    assert h1.get("bold") is True, "level_1 must be bold"
    assert h1.get("new_page") is True, "level_1 must start new page"


@skip_no_key
@pytest.mark.asyncio
async def test_live_extract_and_save_creates_template(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """extract: LLM fills config AND saves a new template in the DB."""
    headers = await register_and_login_headers(client, email="live_ext2@example.com")

    files = {"file": ("stp_excerpt.txt", _STP_EXCERPT.encode("utf-8"), "text/plain")}
    resp = await client.post(
        "/api/v1/templates/extract",
        files=files,
        params={"name": "Тест извлечения из СТП"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert "id" in body, "Response must contain template id"
    assert body["name"] == "Тест извлечения из СТП"
    assert body["type"] == "personal"

    tmpl_id = body["id"]

    # Verify the template is actually retrievable and its JSON has the page margins
    get_resp = await client.get(f"/api/v1/templates/{tmpl_id}", headers=headers)
    assert get_resp.status_code == 200, get_resp.text

    saved_cfg = get_resp.json()["template_json"]
    page = saved_cfg.get("page") or {}
    assert page.get("margin_left_mm") == 30.0


@skip_no_key
@pytest.mark.asyncio
async def test_live_full_pipeline_with_extracted_template(
    client: AsyncClient, db_session: AsyncSession, uploads_dir
) -> None:
    """End-to-end: extract template from standard → segment doc with it → format → export."""
    headers = await register_and_login_headers(client, email="live_ext3@example.com")

    # Step 1: extract template from standard text
    files = {"file": ("stp_excerpt.txt", _STP_EXCERPT.encode("utf-8"), "text/plain")}
    ext = await client.post(
        "/api/v1/templates/extract",
        files=files,
        params={"name": "Авто-шаблон СТП"},
        headers=headers,
    )
    assert ext.status_code == 200, f"extract failed: {ext.text}"
    tmpl_id = ext.json()["id"]

    # Step 2: upload a document
    doc_id = await _upload_doc(client, headers)

    # Step 3: segment with the extracted template
    seg = await client.post(
        f"/api/v1/documents/{doc_id}/segment",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert seg.status_code == 200, f"segment failed: {seg.text}"
    assert len(seg.json()["sections"]) >= 1

    # Step 4: format
    fmt = await client.post(
        f"/api/v1/documents/{doc_id}/format",
        json={"template_id": tmpl_id},
        headers=headers,
    )
    assert fmt.status_code == 200, f"format failed: {fmt.text}"

    # Step 5: export
    exp = await client.get(f"/api/v1/documents/{doc_id}/export/docx", headers=headers)
    assert exp.status_code == 200, f"export failed: {exp.text}"
    assert exp.content[:2] == b"PK"
