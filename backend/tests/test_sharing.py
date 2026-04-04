"""Tests for sharing platform (23 cases)."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


async def _create_voting_topic(
    client: AsyncClient, admin_token: str, class_id: str, title: str = "Topic"
) -> dict:
    """Helper: create a voting-status topic via admin API."""
    resp = await client.post(
        "/api/admin/sharing/topics",
        json={"title": title, "class_id": class_id, "status": "voting"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 201
    return resp.json()


# ============================================================================
# 7.1 Student side
# ============================================================================


async def test_student_list_topics(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#89 — Student lists topics."""
    token, class_id = admin_with_class
    await _create_voting_topic(client, token, class_id)

    resp = await client.get(
        "/api/sharing/topics", headers=auth_header(student_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert "vote_count" in item
    assert "current_user_voted" in item
    assert "total_votes" in data


async def test_student_list_topics_filter_by_status(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#90 — Filter topics by status."""
    token, class_id = admin_with_class
    await _create_voting_topic(client, token, class_id, "Voting Topic")

    resp = await client.get(
        "/api/sharing/topics?status=voting",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "voting"


async def test_student_vote_topic(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#91 — Student votes on a topic."""
    token, class_id = admin_with_class
    topic = await _create_voting_topic(client, token, class_id)

    resp = await client.post(
        f"/api/sharing/topics/{topic['id']}/vote",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200
    assert resp.json()["vote_count"] == 1


async def test_student_vote_topic_duplicate(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#92 — Duplicate vote."""
    token, class_id = admin_with_class
    topic = await _create_voting_topic(client, token, class_id)

    await client.post(
        f"/api/sharing/topics/{topic['id']}/vote",
        headers=auth_header(student_token),
    )
    resp = await client.post(
        f"/api/sharing/topics/{topic['id']}/vote",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 409
    assert "已投过票" in resp.json()["detail"]


async def test_student_vote_topic_max_reached(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#93 — Exceeds max votes per student (3)."""
    token, class_id = admin_with_class

    # Vote on 3 topics
    for i in range(3):
        topic = await _create_voting_topic(client, token, class_id, f"Max{i}")
        await client.post(
            f"/api/sharing/topics/{topic['id']}/vote",
            headers=auth_header(student_token),
        )

    # 4th vote should fail
    topic4 = await _create_voting_topic(client, token, class_id, "Max3")
    resp = await client.post(
        f"/api/sharing/topics/{topic4['id']}/vote",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400
    assert "最多投" in resp.json()["detail"]


async def test_student_vote_non_voting_topic(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#94 — Vote on non-voting topic."""
    token, class_id = admin_with_class
    resp = await client.post(
        "/api/admin/sharing/topics",
        json={
            "title": "Confirmed",
            "class_id": class_id,
            "status": "confirmed",
        },
        headers=auth_header(token),
    )
    topic = resp.json()

    resp = await client.post(
        f"/api/sharing/topics/{topic['id']}/vote",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400
    assert "该主题不在投票中" in resp.json()["detail"]


async def test_student_vote_other_class_topic(
    client: AsyncClient,
    student_token: str,
    another_admin_with_class: tuple[str, str],
):
    """#95 — Vote on another class's topic."""
    other_token, other_class_id = another_admin_with_class
    topic = await _create_voting_topic(client, other_token, other_class_id)

    resp = await client.post(
        f"/api/sharing/topics/{topic['id']}/vote",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 403


async def test_student_unvote_topic(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#96 — Unvote a topic."""
    token, class_id = admin_with_class
    topic = await _create_voting_topic(client, token, class_id)

    await client.post(
        f"/api/sharing/topics/{topic['id']}/vote",
        headers=auth_header(student_token),
    )
    resp = await client.delete(
        f"/api/sharing/topics/{topic['id']}/vote",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200
    assert resp.json()["vote_count"] == 0


async def test_student_unvote_not_voted(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#97 — Unvote a topic not voted on."""
    token, class_id = admin_with_class
    topic = await _create_voting_topic(client, token, class_id)

    resp = await client.delete(
        f"/api/sharing/topics/{topic['id']}/vote",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 404
    assert "未投过票" in resp.json()["detail"]


async def test_student_suggest_topic(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#98 — Student suggests a topic (auto-votes)."""
    resp = await client.post(
        "/api/sharing/topics/suggest",
        json={"title": "My Suggestion"},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 201
    assert resp.json()["vote_count"] == 1


async def test_student_suggest_topic_empty_title(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#99 — Suggest with empty title."""
    resp = await client.post(
        "/api/sharing/topics/suggest",
        json={"title": ""},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400
    assert "标题不能为空" in resp.json()["detail"]


async def test_student_suggest_topic_max_votes_reached(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#100 — Suggest topic when votes are exhausted."""
    token, class_id = admin_with_class

    # Use up all 3 votes
    for i in range(3):
        topic = await _create_voting_topic(client, token, class_id, f"Fill{i}")
        await client.post(
            f"/api/sharing/topics/{topic['id']}/vote",
            headers=auth_header(student_token),
        )

    resp = await client.post(
        "/api/sharing/topics/suggest",
        json={"title": "One More"},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400


async def test_student_get_topic_materials(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#101 — View completed topic's materials."""
    token, class_id = admin_with_class
    resp = await client.post(
        "/api/admin/sharing/topics",
        json={
            "title": "Done Topic",
            "class_id": class_id,
            "status": "completed",
            "presenters": "Alice",
            "session_number": 1,
            "materials_content": "# Slides content",
        },
        headers=auth_header(token),
    )
    topic = resp.json()

    resp = await client.get(
        f"/api/sharing/topics/{topic['id']}/materials",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200
    assert resp.json()["materials_content"] == "# Slides content"


async def test_student_get_topic_materials_not_completed(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    student_token: str,
):
    """#102 — View materials of non-completed topic."""
    token, class_id = admin_with_class
    topic = await _create_voting_topic(client, token, class_id)

    resp = await client.get(
        f"/api/sharing/topics/{topic['id']}/materials",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 404
    assert "暂无素材" in resp.json()["detail"]


# ============================================================================
# 7.2 Admin side
# ============================================================================


async def test_admin_list_topics(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#103 — Admin lists all topics."""
    token, class_id = admin_with_class
    await _create_voting_topic(client, token, class_id)

    resp = await client.get(
        "/api/admin/sharing/topics", headers=auth_header(token)
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1


async def test_admin_list_topics_filter_by_class(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#104 — Admin filters topics by class."""
    token, class_id = admin_with_class
    await _create_voting_topic(client, token, class_id)

    resp = await client.get(
        f"/api/admin/sharing/topics?class_id={class_id}",
        headers=auth_header(token),
    )
    assert resp.status_code == 200


async def test_admin_create_topic(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#105 — Admin creates a topic."""
    token, class_id = admin_with_class
    resp = await client.post(
        "/api/admin/sharing/topics",
        json={"title": "Admin Topic", "class_id": class_id},
        headers=auth_header(token),
    )
    assert resp.status_code == 201


async def test_admin_create_completed_topic_missing_presenters(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#106 — Completed topic without presenters."""
    token, class_id = admin_with_class
    resp = await client.post(
        "/api/admin/sharing/topics",
        json={
            "title": "T",
            "class_id": class_id,
            "status": "completed",
            "session_number": 1,
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 400


async def test_admin_create_completed_topic_missing_session_number(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#107 — Completed topic without session_number."""
    token, class_id = admin_with_class
    resp = await client.post(
        "/api/admin/sharing/topics",
        json={
            "title": "T",
            "class_id": class_id,
            "status": "completed",
            "presenters": "Bob",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 400


async def test_admin_update_topic(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#108 — Update a topic."""
    token, class_id = admin_with_class
    topic = await _create_voting_topic(client, token, class_id)

    resp = await client.patch(
        f"/api/admin/sharing/topics/{topic['id']}",
        json={"title": "Updated Title"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


async def test_admin_update_topic_other_admins(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    another_admin_with_class: tuple[str, str],
):
    """#109 — Cannot update another admin's topic."""
    other_token, other_class_id = another_admin_with_class
    topic = await _create_voting_topic(client, other_token, other_class_id)

    token, _ = admin_with_class
    resp = await client.patch(
        f"/api/admin/sharing/topics/{topic['id']}",
        json={"title": "Hijack"},
        headers=auth_header(token),
    )
    assert resp.status_code == 404


async def test_admin_delete_topic(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#110 — Delete topic cascades votes."""
    token, class_id = admin_with_class
    topic = await _create_voting_topic(client, token, class_id)

    resp = await client.delete(
        f"/api/admin/sharing/topics/{topic['id']}",
        headers=auth_header(token),
    )
    assert resp.status_code == 204


async def test_admin_delete_nonexistent_topic(
    client: AsyncClient, admin_token: str
):
    """#111 — Delete nonexistent topic."""
    resp = await client.delete(
        f"/api/admin/sharing/topics/{uuid.uuid4()}",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404
