"""Tests for model configuration (6 cases)."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


async def _create_model(client: AsyncClient, token: str, name: str = "my-model") -> dict:
    """Helper: create a model config."""
    resp = await client.post(
        "/api/admin/models",
        json={
            "name": name,
            "api_key": "sk-test",
            "base_url": "https://api.example.com",
            "adapter_type": "openai",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    return resp.json()


async def test_admin_list_models(
    client: AsyncClient, admin_token: str
):
    """#112 — List own model configs."""
    resp = await client.get(
        "/api/admin/models", headers=auth_header(admin_token)
    )
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_admin_create_model(
    client: AsyncClient, admin_token: str
):
    """#113 — Create a model config."""
    data = await _create_model(client, admin_token)
    assert data["name"] == "my-model"
    assert data["adapter_type"] == "openai"


async def test_admin_create_model_duplicate_name(
    client: AsyncClient, admin_token: str
):
    """#114 — Duplicate model name."""
    await _create_model(client, admin_token, "dup-model")
    resp = await client.post(
        "/api/admin/models",
        json={
            "name": "dup-model",
            "api_key": "sk-2",
            "base_url": "https://other.com",
            "adapter_type": "openai",
        },
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400
    assert "模型名称已存在" in resp.json()["detail"]


async def test_admin_activate_model(
    client: AsyncClient, admin_token: str
):
    """#115 — Activate a model (deactivates others)."""
    m1 = await _create_model(client, admin_token, "m1")
    m2 = await _create_model(client, admin_token, "m2")

    resp = await client.put(
        f"/api/admin/models/{m1['id']}/activate",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "模型已激活"

    # Activate m2 — m1 should deactivate
    resp = await client.put(
        f"/api/admin/models/{m2['id']}/activate",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200

    # Verify only m2 is active
    resp = await client.get(
        "/api/admin/models", headers=auth_header(admin_token)
    )
    for item in resp.json()["items"]:
        if item["id"] == m2["id"]:
            assert item["is_active"] is True
        else:
            assert item["is_active"] is False


async def test_admin_activate_nonexistent_model(
    client: AsyncClient, admin_token: str
):
    """#116 — Activate nonexistent model."""
    resp = await client.put(
        f"/api/admin/models/{uuid.uuid4()}/activate",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


async def test_admin_activate_other_admins_model(
    client: AsyncClient,
    admin_token: str,
    another_admin_token: str,
):
    """#117 — Cannot activate another admin's model."""
    model = await _create_model(client, another_admin_token, "other-model")

    resp = await client.put(
        f"/api/admin/models/{model['id']}/activate",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 403
