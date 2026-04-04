"""Tests for super admin operations (10 cases)."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


async def test_super_admin_list_admins(
    client: AsyncClient, super_admin_token: str, admin_token: str
):
    """#26 — List all admins with class counts."""
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert "username" in item
    assert "is_active" in item
    assert "class_count" in item


async def test_super_admin_create_admin(
    client: AsyncClient, super_admin_token: str
):
    """#27 — Create a new admin."""
    resp = await client.post(
        "/api/super-admin/admins",
        json={"username": "newadmin", "password": "newpass"},
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newadmin"
    assert data["role"] == "admin"


async def test_super_admin_create_admin_duplicate(
    client: AsyncClient, super_admin_token: str, admin_token: str
):
    """#28 — Duplicate admin username."""
    resp = await client.post(
        "/api/super-admin/admins",
        json={"username": "testadmin", "password": "x"},
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 400
    assert "该账号已存在" in resp.json()["detail"]


async def test_super_admin_toggle_admin_active(
    client: AsyncClient, super_admin_token: str, admin_token: str
):
    """#29 — Toggle admin active status."""
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    admin_id = resp.json()["items"][0]["id"]

    resp = await client.put(
        f"/api/super-admin/admins/{admin_id}/toggle-active",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Toggle back
    resp = await client.put(
        f"/api/super-admin/admins/{admin_id}/toggle-active",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


async def test_super_admin_cannot_disable_self(
    client: AsyncClient, super_admin_token: str, db_session
):
    """#30 — Super admin cannot disable themselves."""
    from auth.jwt import decode_access_token

    payload = decode_access_token(super_admin_token)
    self_id = payload["sub"]

    resp = await client.put(
        f"/api/super-admin/admins/{self_id}/toggle-active",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 400
    assert "不能禁用自己的账号" in resp.json()["detail"]


async def test_super_admin_toggle_nonexistent_admin(
    client: AsyncClient, super_admin_token: str
):
    """#31 — Toggle nonexistent admin."""
    resp = await client.put(
        f"/api/super-admin/admins/{uuid.uuid4()}/toggle-active",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 404


async def test_super_admin_delete_admin(
    client: AsyncClient, super_admin_token: str, admin_with_class: tuple[str, str]
):
    """#32 — Delete admin and all associated data."""
    # Get admin id
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    admin_id = resp.json()["items"][0]["id"]

    resp = await client.delete(
        f"/api/super-admin/admins/{admin_id}",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 204

    # Verify admin is gone
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    ids = [a["id"] for a in resp.json()["items"]]
    assert admin_id not in ids


async def test_super_admin_cannot_delete_self(
    client: AsyncClient, super_admin_token: str
):
    """#33 — Super admin cannot delete themselves."""
    from auth.jwt import decode_access_token

    payload = decode_access_token(super_admin_token)
    self_id = payload["sub"]

    resp = await client.delete(
        f"/api/super-admin/admins/{self_id}",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 400
    assert "不能删除自己的账号" in resp.json()["detail"]


async def test_super_admin_delete_nonexistent_admin(
    client: AsyncClient, super_admin_token: str
):
    """#34 — Delete nonexistent admin."""
    resp = await client.delete(
        f"/api/super-admin/admins/{uuid.uuid4()}",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.xfail(reason="功能未实现: 超级管理员重置老师密码")
async def test_super_admin_reset_admin_password(
    client: AsyncClient, super_admin_token: str, admin_token: str
):
    """#35 — Super admin can reset an admin's password."""
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    admin_id = resp.json()["items"][0]["id"]

    resp = await client.put(
        f"/api/super-admin/admins/{admin_id}/reset-password",
        json={"new_password": "newpass123"},
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 200

    # Verify admin can login with new password
    resp = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "newpass123"},
    )
    assert resp.status_code == 200
