"""Tests for section hints (Stage 5.3)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import register_and_login_headers
from tests.test_segmentation import SAMPLE_TEXT, WORK_STRUCTURE_JSON, LLM_RESPONSE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HINTS_LLM_RESPONSE = json.dumps([
    "Добавьте обзор существующих методов решения задачи.",
    "Укажите критерии выбора подхода.",
    "Приведите сравнительную таблицу аналогов.",
])


async def _setup_segmented_doc(client: AsyncClient, headers: dict) -> tuple[str, str]:
    """Upload a doc, create a template, segment it. Return (doc_id, section_id)."""
    files = {"file": ("doc.txt", SAMPLE_TEXT.encode(), "text/plain")}
    up = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]

    tmpl = await client.post(
        "/api/v1/templates/",
        json={
            "name": "Hints Template",
            "type": "personal",
            "template_json": {"work_structure": WORK_STRUCTURE_JSON},
        },
        headers=headers,
    )
    assert tmpl.status_code == 201, tmpl.text
    tmpl_id = tmpl.json()["id"]

    with patch(
        "app.services.segmentation_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=LLM_RESPONSE,
    ):
        seg = await client.post(
            f"/api/v1/documents/{doc_id}/segment",
            json={"template_id": tmpl_id},
            headers=headers,
        )
    assert seg.status_code == 200, seg.text
    sections = seg.json()["sections"]
    assert len(sections) > 0
    section_id = sections[0]["id"]
    return doc_id, section_id


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hints_returns_200(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await register_and_login_headers(client, email="hints1@example.com")
    doc_id, section_id = await _setup_segmented_doc(client, headers)

    with patch(
        "app.services.hints_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=HINTS_LLM_RESPONSE,
    ):
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/sections/{section_id}/hints",
            headers=headers,
        )

    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_hints_response_shape(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await register_and_login_headers(client, email="hints2@example.com")
    doc_id, section_id = await _setup_segmented_doc(client, headers)

    with patch(
        "app.services.hints_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=HINTS_LLM_RESPONSE,
    ):
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/sections/{section_id}/hints",
            headers=headers,
        )

    body = resp.json()
    assert "hints" in body
    assert "section_id" in body
    assert body["section_id"] == section_id
    assert isinstance(body["hints"], list)
    assert len(body["hints"]) >= 1


@pytest.mark.asyncio
async def test_hints_llm_json_with_markdown(client: AsyncClient, db_session: AsyncSession) -> None:
    """LLM wraps response in ```json ... ``` — must be parsed correctly."""
    headers = await register_and_login_headers(client, email="hints3@example.com")
    doc_id, section_id = await _setup_segmented_doc(client, headers)

    wrapped = f"```json\n{HINTS_LLM_RESPONSE}\n```"
    with patch(
        "app.services.hints_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value=wrapped,
    ):
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/sections/{section_id}/hints",
            headers=headers,
        )

    assert resp.status_code == 200
    assert len(resp.json()["hints"]) == 3


@pytest.mark.asyncio
async def test_hints_invalid_json_from_llm_returns_502(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await register_and_login_headers(client, email="hints4@example.com")
    doc_id, section_id = await _setup_segmented_doc(client, headers)

    with patch(
        "app.services.hints_service.openrouter_service.chat_completion",
        new_callable=AsyncMock,
        return_value="not valid json",
    ):
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/sections/{section_id}/hints",
            headers=headers,
        )

    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_hints_404_wrong_document(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await register_and_login_headers(client, email="hints5@example.com")
    resp = await client.post(
        f"/api/v1/documents/{uuid4()}/sections/{uuid4()}/hints",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hints_404_wrong_section(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await register_and_login_headers(client, email="hints6@example.com")
    files = {"file": ("doc.txt", SAMPLE_TEXT.encode(), "text/plain")}
    up = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    doc_id = up.json()["id"]

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/sections/{uuid4()}/hints",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hints_401_no_auth(client: AsyncClient, db_session: AsyncSession) -> None:
    resp = await client.post(f"/api/v1/documents/{uuid4()}/sections/{uuid4()}/hints")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_hints_cannot_access_other_users_doc(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_h = await register_and_login_headers(client, email="howner@example.com")
    attacker_h = await register_and_login_headers(
        client, email="hattack@example.com", password="ValidPass2"
    )
    doc_id, section_id = await _setup_segmented_doc(client, owner_h)

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/sections/{section_id}/hints",
        headers=attacker_h,
    )
    assert resp.status_code == 404
