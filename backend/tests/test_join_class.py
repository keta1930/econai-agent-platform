"""Tests for join-class and switch-class flows (6 cases)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    auth_header,
    _register_student_via_api,
    _join_class_via_api,
    _login,
)


async def test_join_class_valid_token(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
):
    """Student joins a class with a valid join token."""
    _, class_id, join_token = admin_with_class

    await _register_student_via_api(client, "JOIN001", "pass")
    temp_token = await _login(client, "JOIN001", "pass")

    data = await _join_class_via_api(client, temp_token, join_token)
    assert data["class_id"] == class_id
    assert data["class_name"] == "TestClass"
    assert "access_token" in data
    assert "refresh_token" in data


async def test_join_class_invalid_token(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
):
    """Invalid join token is rejected."""
    await _register_student_via_api(client, "JOIN002", "pass")
    temp_token = await _login(client, "JOIN002", "pass")

    resp = await client.post(
        "/api/student/join-class",
        json={"join_token": "nonexistent-token"},
        headers=auth_header(temp_token),
    )
    assert resp.status_code == 400
    assert "班级 token 无效" in resp.json()["detail"]


async def test_join_class_already_member(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
):
    """Joining a class twice is rejected."""
    _, _, join_token = admin_with_class

    await _register_student_via_api(client, "JOIN003", "pass")
    temp_token = await _login(client, "JOIN003", "pass")

    join_data = await _join_class_via_api(client, temp_token, join_token)
    new_token = join_data["access_token"]

    resp = await client.post(
        "/api/student/join-class",
        json={"join_token": join_token},
        headers=auth_header(new_token),
    )
    assert resp.status_code == 400
    assert "你已在该班级中" in resp.json()["detail"]


async def test_join_class_auto_match_roster(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    db_session: AsyncSession,
):
    """Joining auto-matches the student against the expected roster."""
    admin_tok, class_id, join_token = admin_with_class

    # Add student to expected roster first
    resp = await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "MATCH001"},
        headers=auth_header(admin_tok),
    )
    assert resp.status_code == 201

    # Register and join
    await _register_student_via_api(client, "MATCH001", "pass")
    temp_token = await _login(client, "MATCH001", "pass")
    await _join_class_via_api(client, temp_token, join_token)

    # Verify the class_members record exists
    from models.class_member import ClassMember
    from models.user import User

    user_result = await db_session.execute(
        select(User).where(User.username == "MATCH001")
    )
    user = user_result.scalar_one()
    member_result = await db_session.execute(
        select(ClassMember).where(
            ClassMember.user_id == user.id,
            ClassMember.class_id == class_id,
        )
    )
    assert member_result.scalar_one_or_none() is not None


async def test_switch_class_success(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    another_admin_with_class: tuple[str, str, str],
):
    """Student switches between two joined classes."""
    _, class_id_a, join_token_a = admin_with_class
    _, class_id_b, join_token_b = another_admin_with_class

    await _register_student_via_api(client, "SWITCH001", "pass")
    temp_token = await _login(client, "SWITCH001", "pass")

    # Join both classes
    join_a = await _join_class_via_api(client, temp_token, join_token_a)
    token_a = join_a["access_token"]
    await _join_class_via_api(client, token_a, join_token_b)

    # Login again to get multi-class response
    resp = await client.post(
        "/api/auth/login",
        json={"username": "SWITCH001", "password": "pass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("requires_class_selection") is True

    # Select class A via select-class (bearer auth, needs temp token from multi-class)
    # For multi-class, we need to use select-class which requires bearer auth
    # We can use token_a (still valid) to call switch-class
    resp = await client.post(
        "/api/student/switch-class",
        json={"class_id": class_id_b},
        headers=auth_header(token_a),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["class_id"] == class_id_b
    assert "access_token" in data


async def test_switch_class_not_member(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
):
    """Switching to a class the student hasn't joined fails."""
    _, class_id, join_token = admin_with_class

    await _register_student_via_api(client, "SWITCH002", "pass")
    temp_token = await _login(client, "SWITCH002", "pass")

    # Join one class to get a proper token
    join_data = await _join_class_via_api(client, temp_token, join_token)
    token = join_data["access_token"]

    import uuid
    fake_class_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/student/switch-class",
        json={"class_id": fake_class_id},
        headers=auth_header(token),
    )
    assert resp.status_code == 400
    assert "你不是该班级的成员" in resp.json()["detail"]


async def test_join_class_requires_auth(client: AsyncClient):
    """Join-class without auth returns 401/403."""
    resp = await client.post(
        "/api/student/join-class",
        json={"join_token": "anything"},
    )
    assert resp.status_code in (401, 403)
