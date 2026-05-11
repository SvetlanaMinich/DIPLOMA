import pytest
from httpx import AsyncClient
from tests.conftest import register_and_login_headers


@pytest.fixture
def sample_template_json():
    return {
        "page": {
            "size": "A4",
            "margin_top_mm": 20,
            "margin_bottom_mm": 20,
            "margin_left_mm": 30,
            "margin_right_mm": 15,
        },
        "fonts": {
            "main_family": "Times New Roman",
            "main_size_pt": 14,
            "line_height": 1.5,
            "paragraph_indent_mm": 12.5,
            "text_alignment": "justify",
        },
        "headers": {
            "level_1": {
                "bold": True,
                "uppercase": True,
                "alignment": "center",
                "new_page": True,
            }
        },
        "work_structure": [
            {
                "role": "introduction",
                "title_hints": ["\u0412\u0432\u0435\u0434\u0435\u043d\u0438\u0435"],
                "required": True,
            }
        ],
    }


async def test_create_personal_template(client: AsyncClient, sample_template_json):
    headers = await register_and_login_headers(client)
    payload = {
        "name": "\u041c\u043e\u0439 \u0448\u0430\u0431\u043b\u043e\u043d",
        "description": "\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435",
        "type": "personal",
        "template_json": sample_template_json,
    }
    response = await client.post("/api/v1/templates/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["type"] == "personal"
    assert data["template_json"]["page"]["size"] == "A4"


async def test_get_templates_list(client: AsyncClient, sample_template_json):
    headers = await register_and_login_headers(client)
    await client.post(
        "/api/v1/templates/",
        json={
            "name": "\u0428\u0430\u0431\u043b\u043e\u043d 1",
            "template_json": sample_template_json,
        },
        headers=headers,
    )
    response = await client.get("/api/v1/templates/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


async def test_get_template_by_id(client: AsyncClient, sample_template_json):
    headers = await register_and_login_headers(client)
    create_res = await client.post(
        "/api/v1/templates/",
        json={
            "name": "\u0428\u0430\u0431\u043b\u043e\u043d \u0434\u043b\u044f \u043f\u043e\u0438\u0441\u043a\u0430",
            "template_json": sample_template_json,
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    template_id = create_res.json()["id"]
    response = await client.get(f"/api/v1/templates/{template_id}", headers=headers)
    assert response.status_code == 200
    assert (
        response.json()["name"]
        == "\u0428\u0430\u0431\u043b\u043e\u043d \u0434\u043b\u044f \u043f\u043e\u0438\u0441\u043a\u0430"
    )


async def test_update_template(client: AsyncClient, sample_template_json):
    headers = await register_and_login_headers(client)
    create_res = await client.post(
        "/api/v1/templates/",
        json={
            "name": "\u0421\u0442\u0430\u0440\u043e\u0435 \u0438\u043c\u044f",
            "template_json": sample_template_json,
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    template_id = create_res.json()["id"]
    response = await client.put(
        f"/api/v1/templates/{template_id}",
        json={"name": "\u041d\u043e\u0432\u043e\u0435 \u0438\u043c\u044f"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "\u041d\u043e\u0432\u043e\u0435 \u0438\u043c\u044f"


async def test_delete_template(client: AsyncClient, sample_template_json):
    headers = await register_and_login_headers(client)
    create_res = await client.post(
        "/api/v1/templates/",
        json={
            "name": "\u041d\u0430 \u0443\u0434\u0430\u043b\u0435\u043d\u0438\u0435",
            "template_json": sample_template_json,
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    template_id = create_res.json()["id"]
    del_res = await client.delete(f"/api/v1/templates/{template_id}", headers=headers)
    assert del_res.status_code == 200
    get_res = await client.get(f"/api/v1/templates/{template_id}", headers=headers)
    assert get_res.status_code == 404


async def test_access_denied_for_other_user_template(client: AsyncClient, sample_template_json):
    headers1 = await register_and_login_headers(client, email="user1@example.com")
    create_res = await client.post(
        "/api/v1/templates/",
        json={
            "name": "\u0421\u0435\u043a\u0440\u0435\u0442\u043d\u044b\u0439",
            "template_json": sample_template_json,
        },
        headers=headers1,
    )
    assert create_res.status_code == 201, create_res.text
    template_id = create_res.json()["id"]
    headers2 = await register_and_login_headers(client, email="user2@example.com")
    response = await client.get(f"/api/v1/templates/{template_id}", headers=headers2)
    assert response.status_code == 403
