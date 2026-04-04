"""Tests for authentication and authorization."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    auth_header,
    _create_user_in_db,
    _login,
    _register_student_via_api,
    _join_class_via_api,
    _login_full,
)


# ============================================================================
# 1.1 Student Registration
# ============================================================================


async def test_register_student(client: AsyncClient):
    """Student registers with student_id + college + password."""
    resp = await client.post(
        "/api/auth/register",
        json={
            "student_id": "REG001",
            "college": "lingnan",
            "password": "pass123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "student"
    assert "id" in data


async def test_register_duplicate_student_id(client: AsyncClient):
    """Duplicate student_id is rejected."""
    await _register_student_via_api(client, "DUP001", "lingnan", "p")

    resp = await client.post(
        "/api/auth/register",
        json={
            "student_id": "DUP001",
            "college": "physics",
            "password": "p",
        },
    )
    assert resp.status_code == 400
    assert "该学号已被注册" in resp.json()["detail"]


async def test_register_invalid_college(client: AsyncClient):
    """Invalid college value is rejected by Pydantic validation."""
    resp = await client.post(
        "/api/auth/register",
        json={
            "student_id": "BAD001",
            "college": "math",
            "password": "p",
        },
    )
    assert resp.status_code == 422


async def test_register_no_class_association(
    client: AsyncClient, db_session: AsyncSession
):
    """After registration, student belongs to zero classes."""
    await _register_student_via_api(client, "NOCLASS001", "physics", "p")

    from models.user import User
    from models.class_member import ClassMember
    from sqlalchemy import select

    user = (
        await db_session.execute(select(User).where(User.username == "NOCLASS001"))
    ).scalar_one()
    members = (
        await db_session.execute(
            select(ClassMember).where(ClassMember.user_id == user.id)
        )
    ).scalars().all()
    assert len(members) == 0


# ============================================================================
# 1.2 Login (three variants)
# ============================================================================


async def test_login_student_no_class(
    client: AsyncClient,
):
    """Student with 0 classes gets requires_join_class response."""
    await _register_student_via_api(client, "LONE001", "lingnan", "p")
    data = await _login_full(client, "LONE001", "p")
    assert data.get("requires_join_class") is True
    assert "temp_access_token" in data
    assert "temp_refresh_token" in data


async def test_login_student_single_class(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
):
    """Student with 1 class logs in directly."""
    _, class_id, join_token = admin_with_class

    await _register_student_via_api(client, "SINGLE001", "lingnan", "p")
    temp = await _login(client, "SINGLE001", "p")
    await _join_class_via_api(client, temp, join_token)

    data = await _login_full(client, "SINGLE001", "p")
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["class_id"] == class_id
    assert data["class_name"] == "TestClass"
    assert data.get("admin_name") is not None


async def test_login_student_multi_class(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    another_admin_with_class: tuple[str, str, str],
):
    """Student with N classes gets class selection response."""
    _, _, join_token_a = admin_with_class
    _, _, join_token_b = another_admin_with_class

    await _register_student_via_api(client, "MULTI001", "physics", "p")
    temp = await _login(client, "MULTI001", "p")
    join_a = await _join_class_via_api(client, temp, join_token_a)
    await _join_class_via_api(client, join_a["access_token"], join_token_b)

    data = await _login_full(client, "MULTI001", "p")
    assert data.get("requires_class_selection") is True
    assert len(data["classes"]) == 2


async def test_select_class_bearer_auth(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    another_admin_with_class: tuple[str, str, str],
):
    """Select-class uses Bearer auth (no password needed)."""
    _, class_id_a, join_token_a = admin_with_class
    _, _, join_token_b = another_admin_with_class

    await _register_student_via_api(client, "SEL001", "lingnan", "p")
    temp = await _login(client, "SEL001", "p")
    join_a = await _join_class_via_api(client, temp, join_token_a)
    token = join_a["access_token"]
    await _join_class_via_api(client, token, join_token_b)

    # Login gives multi-class. We use an existing token for select-class.
    resp = await client.post(
        "/api/auth/login/select-class",
        json={"class_id": class_id_a},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["class_id"] == class_id_a
    assert "access_token" in data


async def test_login_admin_unchanged(client: AsyncClient, admin_token: str):
    """Admin login flow is unchanged."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "adminpass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "admin"


async def test_login_super_admin_unchanged(
    client: AsyncClient, super_admin_token: str
):
    """Super admin login flow is unchanged."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "superadmin", "password": "superpass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "super_admin"
    assert "access_token" in data


async def test_login_wrong_password(client: AsyncClient, admin_token: str):
    """Wrong password returns 401."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "WRONG"},
    )
    assert resp.status_code == 401
    assert "用户名或密码错误" in resp.json()["detail"]


async def test_login_nonexistent_user(client: AsyncClient):
    """Nonexistent user returns 401."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "x"},
    )
    assert resp.status_code == 401


async def test_login_disabled_account(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Disabled student account returns 403."""
    await _register_student_via_api(client, "DIS001", "lingnan", "p")

    from models.user import User
    from sqlalchemy import update

    await db_session.execute(
        update(User).where(User.username == "DIS001").values(is_active=False)
    )
    await db_session.commit()

    resp = await client.post(
        "/api/auth/login",
        json={"username": "DIS001", "password": "p"},
    )
    assert resp.status_code == 403
    assert "禁用" in resp.json()["detail"]


# ============================================================================
# 1.3 Password management
# ============================================================================


async def test_change_password_success(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
):
    """Student changes password successfully."""
    _, _, join_token = admin_with_class

    await _register_student_via_api(client, "PWD001", "lingnan", "oldpass")
    temp = await _login(client, "PWD001", "oldpass")
    join_data = await _join_class_via_api(client, temp, join_token)
    token = join_data["access_token"]

    resp = await client.post(
        "/api/student/change-password",
        json={"current_password": "oldpass", "new_password": "newpass"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["password_change_count"] == 1

    # Verify new password works
    await _login(client, "PWD001", "newpass")


async def test_change_password_limit_exceeded(
    client: AsyncClient,
    admin_with_class: tuple[str, str, str],
    db_session: AsyncSession,
):
    """Password change rejected after 3 changes."""
    _, _, join_token = admin_with_class

    await _register_student_via_api(client, "PWD002", "physics", "p0")
    temp = await _login(client, "PWD002", "p0")
    join_data = await _join_class_via_api(client, temp, join_token)
    token = join_data["access_token"]

    # Set password_change_count to 3
    from models.user import User
    from sqlalchemy import update

    await db_session.execute(
        update(User).where(User.username == "PWD002").values(password_change_count=3)
    )
    await db_session.commit()

    resp = await client.post(
        "/api/student/change-password",
        json={"current_password": "p0", "new_password": "p1"},
        headers=auth_header(token),
    )
    assert resp.status_code == 400
    assert "上限" in resp.json()["detail"]


# ============================================================================
# 1.4 Token & Permission Interception (kept from original)
# ============================================================================


async def test_access_without_token(client: AsyncClient):
    """No token on protected endpoint."""
    resp = await client.get("/api/admin/classes")
    assert resp.status_code in (401, 403)


async def test_access_with_invalid_token(client: AsyncClient):
    """Forged / invalid token."""
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header("invalid.token.here"),
    )
    assert resp.status_code in (401, 403)


async def test_student_cannot_access_admin_endpoint(
    client: AsyncClient, student_token: str
):
    """Student token on admin endpoint."""
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 403
    assert "需要管理员权限" in resp.json()["detail"]


async def test_admin_cannot_access_super_admin_endpoint(
    client: AsyncClient, admin_token: str
):
    """Admin token on super_admin endpoint."""
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 403
    assert "需要超级管理员权限" in resp.json()["detail"]


async def test_admin_cannot_access_student_endpoint(
    client: AsyncClient, admin_token: str
):
    """Admin token on student endpoint."""
    resp = await client.get(
        "/api/submissions/my",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 403
    assert "需要学生权限" in resp.json()["detail"]


async def test_teacher_registration_unchanged(
    client: AsyncClient, super_admin_token: str
):
    """Teacher registration flow is unaffected by the student overhaul."""
    # Create invite code
    resp = await client.post(
        "/api/super-admin/invite-codes",
        json={"category": "test"},
        headers=auth_header(super_admin_token),
    )
    code = resp.json()["code"]

    resp = await client.post(
        "/api/auth/register-teacher",
        json={"invite_code": code, "username": "newteacher", "password": "tp"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"
