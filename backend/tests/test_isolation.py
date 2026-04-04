"""Tests for data isolation across tenants (13 cases)."""

import uuid
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

from tests.conftest import (
    auth_header,
    _register_student_via_api,
    _join_class_via_api,
    _login,
)


def _mock_storage():
    """Patch MinIO operations."""
    return patch.multiple(
        "services.storage.storage_service",
        put_object=lambda *a, **kw: None,
        put_object_to_bucket=lambda *a, **kw: None,
        presigned_get_url_from_bucket=lambda *a, **kw: "https://url",
        remove_object_from_bucket=lambda *a, **kw: None,
        client=MagicMock(stat_object=MagicMock(return_value=True)),
    )


async def _setup_two_admins(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    another_admin_with_class: tuple[str, str, str],
) -> tuple[tuple[str, str], tuple[str, str]]:
    """Return (token_a, class_id_a), (token_b, class_id_b)."""
    return admin_with_class, another_admin_with_class


# ============================================================================
# Admin isolation
# ============================================================================


async def test_admin_cannot_see_other_admins_classes(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    another_admin_with_class: tuple[str, str, str],
):
    """#126 — Admin A cannot see Admin B's classes."""
    token_a, class_id_a, _ = admin_with_class
    _, class_id_b, _ = another_admin_with_class

    resp = await client.get(
        "/api/admin/classes", headers=auth_header(token_a)
    )
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()["items"]]
    assert class_id_a in ids
    assert class_id_b not in ids


async def test_admin_cannot_see_other_admins_tasks(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    another_admin_with_class: tuple[str, str, str],
):
    """#127 — Admin A cannot see Admin B's tasks."""
    token_a, class_id_a, _ = admin_with_class
    token_b, class_id_b, _ = another_admin_with_class

    # Create task in each class
    await client.post(
        "/api/tasks",
        json={
            "title": "A Task",
            "description": "D",
            "grading_criteria": "",
            "class_id": class_id_a,
        },
        headers=auth_header(token_a),
    )
    resp_b = await client.post(
        "/api/tasks",
        json={
            "title": "B Task",
            "description": "D",
            "grading_criteria": "",
            "class_id": class_id_b,
        },
        headers=auth_header(token_b),
    )
    task_b_id = resp_b.json()["id"]

    resp = await client.get("/api/tasks", headers=auth_header(token_a))
    task_ids = [t["id"] for t in resp.json()["items"]]
    assert task_b_id not in task_ids


async def test_admin_cannot_see_other_admins_topics(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    another_admin_with_class: tuple[str, str, str],
):
    """#128 — Admin A cannot see Admin B's sharing topics."""
    token_a, class_id_a, _ = admin_with_class
    token_b, class_id_b, _ = another_admin_with_class

    resp_b = await client.post(
        "/api/admin/sharing/topics",
        json={"title": "B Topic", "class_id": class_id_b},
        headers=auth_header(token_b),
    )
    topic_b_id = resp_b.json()["id"]

    resp = await client.get(
        "/api/admin/sharing/topics", headers=auth_header(token_a)
    )
    topic_ids = [t["id"] for t in resp.json()["items"]]
    assert topic_b_id not in topic_ids


async def test_admin_cannot_see_other_admins_models(
    client: AsyncClient,
    admin_token: str,
    another_admin_token: str,
):
    """#129 — Admin A cannot see Admin B's model configs."""
    await client.post(
        "/api/admin/models",
        json={
            "name": "B model",
            "api_key": "sk-x",
            "base_url": "https://x.com",
            "adapter_type": "openai",
        },
        headers=auth_header(another_admin_token),
    )

    resp = await client.get(
        "/api/admin/models", headers=auth_header(admin_token)
    )
    names = [m["name"] for m in resp.json()["items"]]
    assert "B model" not in names


async def test_admin_cannot_see_other_admins_backups(
    client: AsyncClient,
    admin_token: str,
    another_admin_token: str,
):
    """#130 — Admin A cannot see Admin B's backups."""
    with _mock_storage():
        await client.post(
            "/api/admin/backups",
            json={"display_name": "B backup"},
            headers=auth_header(another_admin_token),
        )

    with _mock_storage():
        resp = await client.get(
            "/api/admin/backups", headers=auth_header(admin_token)
        )
    names = [b["display_name"] for b in resp.json()["items"]]
    assert "B backup" not in names


async def test_admin_cannot_access_other_admins_roster(
    client: AsyncClient,
    admin_token: str,
    another_admin_with_class: tuple[str, str, str],
):
    """#131 — Admin A cannot access Admin B's roster."""
    _, other_class_id, _ = another_admin_with_class
    resp = await client.get(
        f"/api/admin/classes/{other_class_id}/roster",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


async def test_admin_cannot_delete_other_admins_task(
    client: AsyncClient,
    admin_token: str,
    another_admin_with_class: tuple[str, str, str],
):
    """#132 — Admin A cannot delete Admin B's task."""
    other_token, other_class_id, _ = another_admin_with_class
    resp = await client.post(
        "/api/tasks",
        json={
            "title": "X",
            "description": "D",
            "grading_criteria": "",
            "class_id": other_class_id,
        },
        headers=auth_header(other_token),
    )
    task_id = resp.json()["id"]

    resp = await client.delete(
        f"/api/tasks/{task_id}", headers=auth_header(admin_token)
    )
    assert resp.status_code == 404


async def test_admin_cannot_view_other_admins_student_submissions(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
    another_admin_token: str,
):
    """#133 — Admin A cannot view Admin B's student submissions."""
    token_a, class_id_a, _ = admin_with_class
    # Create task and submission
    resp = await client.post(
        "/api/tasks",
        json={
            "title": "T",
            "description": "D",
            "grading_criteria": "C",
            "class_id": class_id_a,
        },
        headers=auth_header(token_a),
    )
    task = resp.json()
    await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "published"},
        headers=auth_header(token_a),
    )

    with _mock_storage():
        sub_resp = await client.post(
            "/api/submissions",
            data={
                "task_id": task["id"],
                "content_type": "text",
                "text_content": "answer",
            },
            headers=auth_header(student_token),
        )
    student_id = sub_resp.json()["student_id"]

    resp = await client.get(
        f"/api/admin/students/{student_id}/submissions",
        headers=auth_header(another_admin_token),
    )
    assert resp.status_code == 404


# ============================================================================
# Student isolation
# ============================================================================


async def test_student_cannot_see_other_class_tasks(
    client: AsyncClient,
    student_token: str,
    another_admin_with_class: tuple[str, str, str],
):
    """#134 — Student cannot see other class tasks."""
    other_token, other_class_id, _ = another_admin_with_class
    resp = await client.post(
        "/api/tasks",
        json={
            "title": "Other Task",
            "description": "D",
            "grading_criteria": "C",
            "class_id": other_class_id,
        },
        headers=auth_header(other_token),
    )
    task = resp.json()
    await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "published"},
        headers=auth_header(other_token),
    )

    resp = await client.get(
        f"/api/tasks/{task['id']}", headers=auth_header(student_token)
    )
    assert resp.status_code == 404


async def test_student_cannot_submit_to_other_class_task(
    client: AsyncClient,
    student_token: str,
    another_admin_with_class: tuple[str, str, str],
):
    """#135 — Student cannot submit to other class task."""
    other_token, other_class_id, _ = another_admin_with_class
    resp = await client.post(
        "/api/tasks",
        json={
            "title": "X",
            "description": "D",
            "grading_criteria": "C",
            "class_id": other_class_id,
        },
        headers=auth_header(other_token),
    )
    task = resp.json()
    await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "published"},
        headers=auth_header(other_token),
    )

    resp = await client.post(
        "/api/submissions",
        data={
            "task_id": task["id"],
            "content_type": "text",
            "text_content": "x",
        },
        headers=auth_header(student_token),
    )
    assert resp.status_code == 403


async def test_student_cannot_see_other_class_topics(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
    another_admin_with_class: tuple[str, str, str],
):
    """#136 — Student cannot see other class topics."""
    other_token, other_class_id, _ = another_admin_with_class
    resp = await client.post(
        "/api/admin/sharing/topics",
        json={"title": "Other Topic", "class_id": other_class_id},
        headers=auth_header(other_token),
    )
    other_topic_id = resp.json()["id"]

    resp = await client.get(
        "/api/sharing/topics", headers=auth_header(student_token)
    )
    topic_ids = [t["id"] for t in resp.json()["items"]]
    assert other_topic_id not in topic_ids


async def test_student_cannot_vote_other_class_topic(
    client: AsyncClient,
    student_token: str,
    another_admin_with_class: tuple[str, str, str],
):
    """#137 — Student cannot vote on other class topic."""
    other_token, other_class_id, _ = another_admin_with_class
    resp = await client.post(
        "/api/admin/sharing/topics",
        json={
            "title": "Forbidden Topic",
            "class_id": other_class_id,
            "status": "voting",
        },
        headers=auth_header(other_token),
    )
    topic_id = resp.json()["id"]

    resp = await client.post(
        f"/api/sharing/topics/{topic_id}/vote",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 403


async def test_delete_student_only_affects_current_class(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    another_admin_with_class: tuple[str, str, str],
):
    """#138 — Deleting a student in one class does not affect another."""
    token_a, class_id_a, _ = admin_with_class
    token_b, class_id_b, _ = another_admin_with_class

    _, _, join_token_a = admin_with_class
    _, _, join_token_b = another_admin_with_class

    # Add same student to both expected rosters
    for tok, cid in [(token_a, class_id_a), (token_b, class_id_b)]:
        await client.post(
            f"/api/admin/classes/{cid}/roster",
            json={"student_id": "ISO_STU"},
            headers=auth_header(tok),
        )

    # Register once, then join both classes
    await _register_student_via_api(client, "ISO_STU", "lingnan", "p")
    temp_token = await _login(client, "ISO_STU", "p")
    await _join_class_via_api(client, temp_token, join_token_a)
    # Re-login to get updated token, then join class B
    token_after_a = await _login(client, "ISO_STU", "p")
    await _join_class_via_api(client, token_after_a, join_token_b)

    # Delete from class A
    resp = await client.delete(
        f"/api/admin/classes/{class_id_a}/roster/ISO_STU",
        headers=auth_header(token_a),
    )
    assert resp.status_code == 204

    # Student should still exist in class B's expected roster
    resp = await client.get(
        f"/api/admin/classes/{class_id_b}/roster",
        headers=auth_header(token_b),
    )
    expected_ids = [i["student_id"] for i in resp.json()["expected"]]
    assert "ISO_STU" in expected_ids

    # Student can still log in for class B
    resp = await client.post(
        "/api/auth/login",
        json={"username": "ISO_STU", "password": "p"},
    )
    assert resp.status_code == 200
