"""Tests for task management (18 cases)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


async def _create_draft_task(
    client: AsyncClient, token: str, class_id: str, **overrides
) -> dict:
    """Helper: create a draft task and return its JSON."""
    body = {
        "title": overrides.get("title", "Test Task"),
        "description": overrides.get("description", "Task description"),
        "grading_criteria": overrides.get("grading_criteria", ""),
        "class_id": class_id,
    }
    resp = await client.post(
        "/api/tasks", json=body, headers=auth_header(token)
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_published_task(
    client: AsyncClient, token: str, class_id: str
) -> dict:
    """Helper: create and publish a task."""
    task = await _create_draft_task(
        client,
        token,
        class_id,
        title="Published Task",
        description="Desc",
        grading_criteria="Criteria",
    )
    resp = await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "published"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    return resp.json()


# ============================================================================
# Listing
# ============================================================================


async def test_admin_list_tasks(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#54 — Admin lists tasks."""
    token, class_id, _ = admin_with_class
    await _create_draft_task(client, token, class_id)

    resp = await client.get("/api/tasks", headers=auth_header(token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert "title" in items[0]
    assert "status" in items[0]
    assert "class_name" in items[0]


async def test_admin_list_tasks_filter_by_status(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#55 — Filter tasks by status."""
    token, class_id, _ = admin_with_class
    await _create_published_task(client, token, class_id)
    await _create_draft_task(client, token, class_id, title="Draft Only")

    resp = await client.get(
        "/api/tasks?status=published", headers=auth_header(token)
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "published"


async def test_admin_list_tasks_filter_by_class(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#56 — Filter tasks by class_id."""
    token, class_id, _ = admin_with_class
    await _create_draft_task(client, token, class_id)

    resp = await client.get(
        f"/api/tasks?class_id={class_id}", headers=auth_header(token)
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["class_id"] == class_id


async def test_student_list_tasks_only_own_class(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#57 — Student only sees own class tasks."""
    token, class_id, _ = admin_with_class
    await _create_published_task(client, token, class_id)

    resp = await client.get("/api/tasks", headers=auth_header(student_token))
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["class_id"] == class_id


async def test_student_cannot_see_draft_tasks(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#58 — Student cannot access draft tasks."""
    token, class_id, _ = admin_with_class
    task = await _create_draft_task(client, token, class_id)

    resp = await client.get(
        f"/api/tasks/{task['id']}", headers=auth_header(student_token)
    )
    assert resp.status_code == 404


# ============================================================================
# CRUD
# ============================================================================


async def test_admin_create_task_draft(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#59 — Create a draft task."""
    token, class_id, _ = admin_with_class
    task = await _create_draft_task(client, token, class_id)
    assert task["status"] == "draft"


async def test_admin_create_task_invalid_class(
    client: AsyncClient, admin_token: str
):
    """#60 — Create task for invalid class."""
    resp = await client.post(
        "/api/tasks",
        json={
            "title": "T",
            "description": "D",
            "grading_criteria": "",
            "class_id": str(uuid.uuid4()),
        },
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400
    assert "班级不存在" in resp.json()["detail"]


async def test_admin_update_draft_task(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#61 — Update draft task fields."""
    token, class_id, _ = admin_with_class
    task = await _create_draft_task(client, token, class_id)

    resp = await client.patch(
        f"/api/tasks/{task['id']}",
        json={"title": "Updated Title"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


async def test_admin_publish_task(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#62 — Publish a draft task."""
    token, class_id, _ = admin_with_class
    task = await _create_draft_task(
        client,
        token,
        class_id,
        title="Pub",
        description="Desc",
        grading_criteria="Criteria",
    )

    resp = await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "published"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


async def test_admin_publish_task_missing_fields(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#63 — Publish without required fields."""
    token, class_id, _ = admin_with_class
    task = await _create_draft_task(
        client, token, class_id, title="T", description="D", grading_criteria=""
    )

    resp = await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "published"},
        headers=auth_header(token),
    )
    assert resp.status_code == 400
    assert "需要填写" in resp.json()["detail"]


async def test_admin_cannot_edit_published_task(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#64 — Published task cannot be edited."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    resp = await client.patch(
        f"/api/tasks/{task['id']}",
        json={"title": "Changed"},
        headers=auth_header(token),
    )
    assert resp.status_code == 400
    assert "已发布任务不可编辑" in resp.json()["detail"]


async def test_admin_batch_publish(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#65 — Batch publish to multiple classes."""
    token, class_id, _ = admin_with_class

    # Create a second class
    resp = await client.post(
        "/api/admin/classes",
        json={"name": "BatchClass"},
        headers=auth_header(token),
    )
    class_id_2 = resp.json()["id"]

    resp = await client.post(
        "/api/tasks/batch-publish",
        json={
            "title": "Batch Task",
            "description": "Desc",
            "grading_criteria": "Criteria",
            "class_ids": [class_id, class_id_2],
                "status": "published",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert len(resp.json()["created"]) == 2


async def test_admin_batch_publish_invalid_class(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#66 — Batch publish with invalid class_id."""
    token, class_id, _ = admin_with_class
    resp = await client.post(
        "/api/tasks/batch-publish",
        json={
            "title": "T",
            "description": "D",
            "grading_criteria": "C",
            "class_ids": [class_id, str(uuid.uuid4())],
                "status": "published",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 400


async def test_admin_delete_task_cascade(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#67 — Delete task cascades submissions."""
    token, class_id, _ = admin_with_class
    task = await _create_draft_task(client, token, class_id)

    resp = await client.delete(
        f"/api/tasks/{task['id']}", headers=auth_header(token)
    )
    assert resp.status_code == 204

    # Verify task is gone
    resp = await client.get(
        f"/api/tasks/{task['id']}", headers=auth_header(token)
    )
    assert resp.status_code == 404


async def test_admin_delete_nonexistent_task(
    client: AsyncClient, admin_token: str
):
    """#68 — Delete nonexistent task."""
    resp = await client.delete(
        f"/api/tasks/{uuid.uuid4()}", headers=auth_header(admin_token)
    )
    assert resp.status_code == 404


async def test_admin_get_task_stats(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#69 — Get task submission statistics."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    resp = await client.get(
        f"/api/tasks/{task['id']}/stats", headers=auth_header(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_students" in data
    assert "submitted_count" in data
    assert "submission_rate" in data
    assert "not_submitted" in data


async def test_admin_generate_criteria(
    client: AsyncClient, admin_with_class: tuple[str, str, str]
):
    """#70 — Generate grading criteria with AI model configured."""
    token, class_id, _ = admin_with_class

    # Create and activate a model config
    resp = await client.post(
        "/api/admin/models",
        json={
            "name": "test-model",
            "api_key": "sk-test",
            "base_url": "https://api.example.com",
            "adapter_type": "openai",
        },
        headers=auth_header(token),
    )
    model_id = resp.json()["id"]
    await client.put(
        f"/api/admin/models/{model_id}/activate",
        headers=auth_header(token),
    )

    # Mock the actual AI call
    with patch(
        "services.criteria_generator.generate_criteria",
        new_callable=AsyncMock,
        return_value="Generated criteria text",
    ):
        resp = await client.post(
            "/api/tasks/generate-criteria",
            json={"title": "Test", "description": "A task"},
            headers=auth_header(token),
        )
    assert resp.status_code == 200
    assert "criteria" in resp.json()


async def test_admin_generate_criteria_no_model(
    client: AsyncClient, admin_token: str
):
    """#71 — Generate criteria without active model."""
    resp = await client.post(
        "/api/tasks/generate-criteria",
        json={"title": "Test", "description": "A task"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400
    assert "请先配置并激活 AI 模型" in resp.json()["detail"]
