"""Tests for class management (8 cases)."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


async def test_admin_list_classes(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#36 — Admin lists own classes."""
    token, class_id = admin_with_class
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert "name" in items[0]
    assert "student_count" in items[0]


async def test_admin_create_class(client: AsyncClient, admin_token: str):
    """#37 — Create a new class."""
    resp = await client.post(
        "/api/admin/classes",
        json={"name": "NewClass"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "NewClass"
    assert "id" in data


async def test_admin_create_class_duplicate_name(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#38 — Duplicate class name under same admin."""
    token, _ = admin_with_class
    resp = await client.post(
        "/api/admin/classes",
        json={"name": "TestClass"},
        headers=auth_header(token),
    )
    assert resp.status_code == 400
    assert "该班级名称已存在" in resp.json()["detail"]


async def test_different_admins_can_create_same_class_name(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    another_admin_token: str,
):
    """#39 — Different admins can create classes with the same name."""
    resp = await client.post(
        "/api/admin/classes",
        json={"name": "TestClass"},
        headers=auth_header(another_admin_token),
    )
    assert resp.status_code == 201


async def test_admin_delete_class_cascade(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#40 — Delete class cascades all related data."""
    token, class_id = admin_with_class

    # Add some data: roster entry
    await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "DEL001"},
        headers=auth_header(token),
    )

    resp = await client.delete(
        f"/api/admin/classes/{class_id}",
        headers=auth_header(token),
    )
    assert resp.status_code == 204

    # Verify class is gone
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(token),
    )
    ids = [c["id"] for c in resp.json()["items"]]
    assert class_id not in ids


async def test_admin_delete_nonexistent_class(
    client: AsyncClient, admin_token: str
):
    """#41 — Delete nonexistent class."""
    resp = await client.delete(
        f"/api/admin/classes/{uuid.uuid4()}",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


async def test_admin_delete_other_admins_class(
    client: AsyncClient,
    another_admin_with_class: tuple[str, str],
    admin_token: str,
):
    """#42 — Cannot delete another admin's class."""
    _, other_class_id = another_admin_with_class
    resp = await client.delete(
        f"/api/admin/classes/{other_class_id}",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.xfail(reason="功能未实现: 归档班级")
async def test_admin_archive_class(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#43 — Archive a class."""
    token, class_id = admin_with_class
    resp = await client.patch(
        f"/api/admin/classes/{class_id}",
        json={"status": "archived"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"
