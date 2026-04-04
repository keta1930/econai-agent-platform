"""Tests for invite code management (5 cases)."""

import uuid

from httpx import AsyncClient

from tests.conftest import auth_header, _create_invite_code


async def test_create_invite_code(
    client: AsyncClient, super_admin_token: str
):
    """#1 — Super admin creates an invite code with category."""
    resp = await client.post(
        "/api/super-admin/invite-codes",
        json={"category": "物理学院"},
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "code" in data
    assert len(data["code"]) > 0
    assert data["category"] == "物理学院"
    assert data["registered_count"] == 0
    assert "id" in data
    assert "created_at" in data


async def test_list_invite_codes(
    client: AsyncClient, super_admin_token: str
):
    """#2 — List invite codes shows category and registered_count, no code."""
    # Create two codes
    await _create_invite_code(client, super_admin_token, "经济学院")
    code2 = await _create_invite_code(client, super_admin_token, "管理学院")

    # Register a teacher with the second code
    await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": code2,
            "username": "teacher_list",
            "password": "pass123",
        },
    )

    resp = await client.get(
        "/api/super-admin/invite-codes",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    items = data["items"]
    assert len(items) >= 2

    # Find the "管理学院" code and check registered_count
    mgmt_items = [i for i in items if i["category"] == "管理学院"]
    assert len(mgmt_items) == 1
    assert mgmt_items[0]["registered_count"] == 1

    # Ensure no item has a "code" field
    for item in items:
        assert "code" not in item


async def test_delete_invite_code(
    client: AsyncClient, super_admin_token: str
):
    """#3 — Delete invite code; already registered teachers unaffected."""
    code = await _create_invite_code(client, super_admin_token, "删除测试")

    # Register a teacher
    await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": code,
            "username": "teacher_del",
            "password": "pass123",
        },
    )

    # Get the invite code id
    resp = await client.get(
        "/api/super-admin/invite-codes",
        headers=auth_header(super_admin_token),
    )
    del_items = [i for i in resp.json()["items"] if i["category"] == "删除测试"]
    code_id = del_items[0]["id"]

    # Delete
    resp = await client.delete(
        f"/api/super-admin/invite-codes/{code_id}",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 204

    # Verify deleted
    resp = await client.get(
        "/api/super-admin/invite-codes",
        headers=auth_header(super_admin_token),
    )
    ids = [i["id"] for i in resp.json()["items"]]
    assert code_id not in ids

    # Teacher can still log in
    resp = await client.post(
        "/api/auth/login",
        json={"username": "teacher_del", "password": "pass123"},
    )
    assert resp.status_code == 200


async def test_regenerate_invite_code(
    client: AsyncClient, super_admin_token: str
):
    """#4 — Regenerate invite code: new code works, old code fails."""
    old_code = await _create_invite_code(client, super_admin_token, "再生测试")

    # Get the invite code id
    resp = await client.get(
        "/api/super-admin/invite-codes",
        headers=auth_header(super_admin_token),
    )
    regen_items = [i for i in resp.json()["items"] if i["category"] == "再生测试"]
    code_id = regen_items[0]["id"]

    # Regenerate
    resp = await client.post(
        f"/api/super-admin/invite-codes/{code_id}/regenerate",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 200
    new_code = resp.json()["code"]
    assert new_code != old_code

    # Old code should fail
    resp = await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": old_code,
            "username": "teacher_old_code",
            "password": "pass123",
        },
    )
    assert resp.status_code == 400
    assert "邀请码无效" in resp.json()["detail"]

    # New code should work
    resp = await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": new_code,
            "username": "teacher_new_code",
            "password": "pass123",
        },
    )
    assert resp.status_code == 201


async def test_invite_code_forbidden_for_non_super_admin(
    client: AsyncClient, admin_token: str
):
    """#5 — Non-super-admin cannot access invite code endpoints."""
    resp = await client.post(
        "/api/super-admin/invite-codes",
        json={"category": "test"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 403

    resp = await client.get(
        "/api/super-admin/invite-codes",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 403
