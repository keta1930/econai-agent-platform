"""Tests for submission management (17 cases)."""

import io
import uuid
from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


async def _create_published_task(
    client: AsyncClient, admin_token: str, class_id: str
) -> dict:
    """Helper: create and publish a task."""
    resp = await client.post(
        "/api/tasks",
        json={
            "title": "Submit Task",
            "description": "Desc",
            "grading_criteria": "Criteria",
            "class_id": class_id,
        },
        headers=auth_header(admin_token),
    )
    task = resp.json()
    await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "published"},
        headers=auth_header(admin_token),
    )
    return task


def _mock_storage():
    """Context manager that patches storage operations used by submissions."""
    return patch.multiple(
        "services.storage.storage_service",
        put_object=lambda *a, **kw: None,
        presigned_get_url=lambda *a, **kw: "https://example.com/presigned",
        get_text=lambda *a, **kw: "file content",
    )


# ============================================================================
# Student submissions
# ============================================================================


async def test_student_submit_text(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#72 — Student submits text assignment."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    with _mock_storage():
        resp = await client.post(
            "/api/submissions",
            data={
                "task_id": task["id"],
                "content_type": "text",
                "text_content": "My answer",
            },
            headers=auth_header(student_token),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content_type"] == "text"
    assert data["status"] == "pending"


async def test_student_submit_file(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#73 — Student submits file assignment."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    with _mock_storage():
        resp = await client.post(
            "/api/submissions",
            data={"task_id": task["id"], "content_type": "file"},
            files={"file": ("answer.md", b"# My Answer", "text/markdown")},
            headers=auth_header(student_token),
        )
    assert resp.status_code == 201
    assert resp.json()["content_type"] == "file"


async def test_student_submit_image(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#74 — Student submits image assignment (manual_review status)."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    # Minimal valid PNG header
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    )
    with _mock_storage():
        resp = await client.post(
            "/api/submissions",
            data={"task_id": task["id"], "content_type": "image"},
            files={"file": ("photo.png", png_bytes, "image/png")},
            headers=auth_header(student_token),
        )
    assert resp.status_code == 201
    assert resp.json()["content_type"] == "image"
    assert resp.json()["status"] == "manual_review"


async def test_student_submit_wrong_task_class(
    client: AsyncClient,
    student_token: str,
    another_admin_with_class: tuple[str, str, str],
):
    """#75 — Submit to a task in another class."""
    other_token, other_class_id, _ = another_admin_with_class
    task = await _create_published_task(client, other_token, other_class_id)

    with _mock_storage():
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
    assert "无权提交该任务" in resp.json()["detail"]


async def test_student_submit_nonexistent_task(
    client: AsyncClient, student_token: str
):
    """#76 — Submit to nonexistent task."""
    resp = await client.post(
        "/api/submissions",
        data={
            "task_id": str(uuid.uuid4()),
            "content_type": "text",
            "text_content": "x",
        },
        headers=auth_header(student_token),
    )
    assert resp.status_code == 404


async def test_student_submit_invalid_content_type(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#77 — Invalid content_type value."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    resp = await client.post(
        "/api/submissions",
        data={
            "task_id": task["id"],
            "content_type": "video",
            "text_content": "x",
        },
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400


async def test_student_submit_empty_text(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#78 — Submit empty text content."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    resp = await client.post(
        "/api/submissions",
        data={
            "task_id": task["id"],
            "content_type": "text",
            "text_content": "",
        },
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400
    assert "内容不能为空" in resp.json()["detail"]


async def test_student_submit_text_exceeds_limit(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#79 — Text exceeds size limit."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    huge_text = "x" * (3 * 1024 * 1024)  # 3MB > 2MB limit
    resp = await client.post(
        "/api/submissions",
        data={
            "task_id": task["id"],
            "content_type": "text",
            "text_content": huge_text,
        },
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400
    assert "限制" in resp.json()["detail"]


async def test_student_submit_invalid_file_extension(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#80 — Unsupported file extension."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    resp = await client.post(
        "/api/submissions",
        data={"task_id": task["id"], "content_type": "file"},
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400
    assert "仅支持" in resp.json()["detail"]


async def test_student_submit_version_increment(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#81 — Multiple submissions increment version."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    with _mock_storage():
        resp1 = await client.post(
            "/api/submissions",
            data={
                "task_id": task["id"],
                "content_type": "text",
                "text_content": "v1",
            },
            headers=auth_header(student_token),
        )
        assert resp1.json()["version"] == 1

        resp2 = await client.post(
            "/api/submissions",
            data={
                "task_id": task["id"],
                "content_type": "text",
                "text_content": "v2",
            },
            headers=auth_header(student_token),
        )
        assert resp2.json()["version"] == 2


# ============================================================================
# Student list submissions
# ============================================================================


async def test_student_list_my_submissions(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#82 — Student lists own submissions."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    with _mock_storage():
        await client.post(
            "/api/submissions",
            data={
                "task_id": task["id"],
                "content_type": "text",
                "text_content": "answer",
            },
            headers=auth_header(student_token),
        )

    resp = await client.get(
        "/api/submissions/my", headers=auth_header(student_token)
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1


async def test_student_list_my_task_submissions(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#83 — Student lists submissions for a specific task."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    with _mock_storage():
        await client.post(
            "/api/submissions",
            data={
                "task_id": task["id"],
                "content_type": "text",
                "text_content": "a1",
            },
            headers=auth_header(student_token),
        )
        await client.post(
            "/api/submissions",
            data={
                "task_id": task["id"],
                "content_type": "text",
                "text_content": "a2",
            },
            headers=auth_header(student_token),
        )

    resp = await client.get(
        f"/api/submissions/my/{task['id']}", headers=auth_header(student_token)
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


# ============================================================================
# Admin view submissions
# ============================================================================


async def test_admin_get_student_submissions(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
    db_session,
):
    """#84 — Admin views a student's submissions."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

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
        headers=auth_header(token),
    )
    assert resp.status_code == 200


async def test_admin_get_student_submissions_other_class(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
    another_admin_token: str,
    db_session,
):
    """#85 — Admin cannot view other class student's submissions."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    with _mock_storage():
        sub_resp = await client.post(
            "/api/submissions",
            data={
                "task_id": task["id"],
                "content_type": "text",
                "text_content": "x",
            },
            headers=auth_header(student_token),
        )
    student_id = sub_resp.json()["student_id"]

    resp = await client.get(
        f"/api/admin/students/{student_id}/submissions",
        headers=auth_header(another_admin_token),
    )
    assert resp.status_code == 404


async def test_admin_get_submission_content_text(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#86 — Admin views text submission content."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    with _mock_storage():
        sub_resp = await client.post(
            "/api/submissions",
            data={
                "task_id": task["id"],
                "content_type": "text",
                "text_content": "my text",
            },
            headers=auth_header(student_token),
        )
    submission_id = sub_resp.json()["id"]

    with patch(
        "services.storage.storage_service.get_text", return_value="my text"
    ):
        resp = await client.get(
            f"/api/admin/submissions/{submission_id}/content",
            headers=auth_header(token),
        )
    assert resp.status_code == 200
    assert resp.json()["content"] == "my text"


async def test_admin_get_submission_content_image(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#87 — Admin views image submission content (presigned URL)."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    )
    with _mock_storage():
        sub_resp = await client.post(
            "/api/submissions",
            data={"task_id": task["id"], "content_type": "image"},
            files={"file": ("img.png", png_bytes, "image/png")},
            headers=auth_header(student_token),
        )
    submission_id = sub_resp.json()["id"]

    with patch(
        "services.storage.storage_service.presigned_get_url",
        return_value="https://presigned.url/img",
    ):
        resp = await client.get(
            f"/api/admin/submissions/{submission_id}/content",
            headers=auth_header(token),
        )
    assert resp.status_code == 200
    assert "presigned" in resp.json()["content"]


async def test_admin_get_student_task_submissions(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    student_token: str,
):
    """#88 — Admin views a student's submissions for a specific task."""
    token, class_id, _ = admin_with_class
    task = await _create_published_task(client, token, class_id)

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
        f"/api/admin/tasks/{task['id']}/students/{student_id}/submissions",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "student_name" in data
    assert len(data["items"]) >= 1
