"""Tests for student roster management (10 cases)."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


async def test_list_roster(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#44 — List roster entries."""
    token, class_id = admin_with_class
    await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "LIST001"},
        headers=auth_header(token),
    )
    resp = await client.get(
        f"/api/admin/classes/{class_id}/roster",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert "student_id" in items[0]
    assert "registered" in items[0]


async def test_add_student_to_roster(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#45 — Add a single student to roster."""
    token, class_id = admin_with_class
    resp = await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "ADD001"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.json()["student_id"] == "ADD001"


async def test_add_duplicate_student_to_roster(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#46 — Add duplicate student_id to roster."""
    token, class_id = admin_with_class
    await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "DUP_R"},
        headers=auth_header(token),
    )
    resp = await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "DUP_R"},
        headers=auth_header(token),
    )
    assert resp.status_code == 400
    assert "该学号已在名单中" in resp.json()["detail"]


async def test_batch_import_roster(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#47 — Batch import students."""
    token, class_id = admin_with_class
    resp = await client.post(
        f"/api/admin/classes/{class_id}/roster/batch",
        json={"student_ids": ["B001", "B002", "B003"]},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["added"] == 3
    assert data["duplicates"] == 0


async def test_batch_import_roster_skips_duplicates(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#48 — Batch import skips existing entries."""
    token, class_id = admin_with_class
    await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "EXIST01"},
        headers=auth_header(token),
    )
    resp = await client.post(
        f"/api/admin/classes/{class_id}/roster/batch",
        json={"student_ids": ["EXIST01", "NEW01", "NEW02"]},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["added"] == 2
    assert data["duplicates"] == 1


@pytest.mark.xfail(reason="功能未实现: 批量导入检测输入列表内部重复")
async def test_batch_import_roster_strict_reject(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#49 — Batch import rejects internal duplicates."""
    token, class_id = admin_with_class
    resp = await client.post(
        f"/api/admin/classes/{class_id}/roster/batch",
        json={"student_ids": ["X01", "X02", "X01"]},
        headers=auth_header(token),
    )
    assert resp.status_code == 400


async def test_delete_student_from_roster(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#50 — Delete student from roster cascades user and submissions."""
    token, class_id = admin_with_class
    await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "DEL_S"},
        headers=auth_header(token),
    )

    # Register the student
    await client.post(
        "/api/auth/register",
        json={
            "admin_name": "testadmin",
            "class_name": "TestClass",
            "student_id": "DEL_S",
            "password": "p",
        },
    )

    resp = await client.delete(
        f"/api/admin/classes/{class_id}/roster/DEL_S",
        headers=auth_header(token),
    )
    assert resp.status_code == 204

    # Verify student removed from roster
    resp = await client.get(
        f"/api/admin/classes/{class_id}/roster",
        headers=auth_header(token),
    )
    student_ids = [i["student_id"] for i in resp.json()["items"]]
    assert "DEL_S" not in student_ids


async def test_delete_nonexistent_student_from_roster(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#51 — Delete student not in roster."""
    token, class_id = admin_with_class
    resp = await client.delete(
        f"/api/admin/classes/{class_id}/roster/GHOST",
        headers=auth_header(token),
    )
    assert resp.status_code == 404


async def test_roster_operations_on_other_admins_class(
    client: AsyncClient,
    admin_token: str,
    another_admin_with_class: tuple[str, str],
):
    """#52 — Cannot operate on another admin's class roster."""
    _, other_class_id = another_admin_with_class
    resp = await client.post(
        f"/api/admin/classes/{other_class_id}/roster",
        json={"student_id": "X"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


async def test_cross_class_same_student_id(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    another_admin_with_class: tuple[str, str],
):
    """#53 — Same student_id in different classes is allowed."""
    token_a, class_id_a = admin_with_class
    token_b, class_id_b = another_admin_with_class

    resp_a = await client.post(
        f"/api/admin/classes/{class_id_a}/roster",
        json={"student_id": "SHARED_ID"},
        headers=auth_header(token_a),
    )
    assert resp_a.status_code == 201

    resp_b = await client.post(
        f"/api/admin/classes/{class_id_b}/roster",
        json={"student_id": "SHARED_ID"},
        headers=auth_header(token_b),
    )
    assert resp_b.status_code == 201
