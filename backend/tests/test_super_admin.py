"""Tests for super admin operations."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, _login_full


async def test_super_admin_list_admins(
    client: AsyncClient, super_admin_token: str, admin_token: str
):
    """#26 — List all admins with class counts and category."""
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
    assert "category" in item


async def test_super_admin_toggle_admin_active(
    client: AsyncClient, super_admin_token: str, admin_token: str
):
    """#29 — Toggle admin active status; disabling revokes refresh tokens."""
    # Login to get refresh token
    login_data = await _login_full(client, "testadmin", "adminpass")
    refresh_token = login_data["refresh_token"]

    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    admin_id = resp.json()["items"][0]["id"]

    # Disable
    resp = await client.put(
        f"/api/super-admin/admins/{admin_id}/toggle-active",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Verify refresh token was revoked
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 401

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
    client: AsyncClient, super_admin_token: str, admin_with_class: tuple[str, str, str]
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
