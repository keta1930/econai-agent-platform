"""Tests for authentication and authorization (25 cases)."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, _create_user_in_db, _login


# ============================================================================
# 1.1 Student Registration
# ============================================================================


async def test_register_student_success(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#1 — Student registers with valid credentials."""
    token, class_id = admin_with_class
    await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "REG001"},
        headers=auth_header(token),
    )
    resp = await client.post(
        "/api/auth/register",
        json={
            "admin_name": "testadmin",
            "class_name": "TestClass",
            "student_id": "REG001",
            "password": "pass123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "student"
    assert "id" in data


async def test_register_student_admin_not_found(client: AsyncClient):
    """#2 — Register with nonexistent admin name."""
    resp = await client.post(
        "/api/auth/register",
        json={
            "admin_name": "ghost",
            "class_name": "AnyClass",
            "student_id": "S1",
            "password": "p",
        },
    )
    assert resp.status_code == 404
    assert "管理员不存在" in resp.json()["detail"]


async def test_register_student_class_not_found(
    client: AsyncClient, admin_token: str
):
    """#3 — Admin exists but class name does not match."""
    resp = await client.post(
        "/api/auth/register",
        json={
            "admin_name": "testadmin",
            "class_name": "Nonexistent",
            "student_id": "S1",
            "password": "p",
        },
    )
    assert resp.status_code == 404
    assert "班级不存在" in resp.json()["detail"]


async def test_register_student_not_in_roster(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#4 — student_id not in roster."""
    resp = await client.post(
        "/api/auth/register",
        json={
            "admin_name": "testadmin",
            "class_name": "TestClass",
            "student_id": "UNKNOWN",
            "password": "p",
        },
    )
    assert resp.status_code == 400
    assert "学号不在该班级名单中" in resp.json()["detail"]


async def test_register_student_duplicate(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#5 — Same student_id registers twice in the same class."""
    token, class_id = admin_with_class
    await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "DUP001"},
        headers=auth_header(token),
    )
    register_body = {
        "admin_name": "testadmin",
        "class_name": "TestClass",
        "student_id": "DUP001",
        "password": "p",
    }
    resp1 = await client.post("/api/auth/register", json=register_body)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/auth/register", json=register_body)
    assert resp2.status_code == 400
    assert "该学号已在此班级注册" in resp2.json()["detail"]


@pytest.mark.xfail(reason="功能未实现: 学生注册时自动加入多班级")
async def test_register_student_auto_join_multi_class(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#6 — Auto-join all classes under same admin that imported the student_id."""
    token, class_id = admin_with_class
    # Create second class under same admin
    resp = await client.post(
        "/api/admin/classes",
        json={"name": "SecondClass"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    class_id2 = resp.json()["id"]

    # Add same student to both rosters
    for cid in [class_id, class_id2]:
        await client.post(
            f"/api/admin/classes/{cid}/roster",
            json={"student_id": "MULTI001"},
            headers=auth_header(token),
        )

    resp = await client.post(
        "/api/auth/register",
        json={
            "admin_name": "testadmin",
            "class_name": "TestClass",
            "student_id": "MULTI001",
            "password": "p",
        },
    )
    assert resp.status_code == 201

    # Verify student can log in to BOTH classes (not just the one they registered with)
    for class_name in ["TestClass", "SecondClass"]:
        login_resp = await client.post(
            "/api/auth/login",
            json={
                "admin_name": "testadmin",
                "class_name": class_name,
                "student_id": "MULTI001",
                "password": "p",
            },
        )
        assert login_resp.status_code == 200, f"Should be able to login to {class_name}"


@pytest.mark.xfail(reason="功能未实现: 注册时提供姓名字段")
async def test_register_student_with_name_field(
    client: AsyncClient, admin_with_class: tuple[str, str]
):
    """#7 — Register with display_name field."""
    token, class_id = admin_with_class
    await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "NAME001"},
        headers=auth_header(token),
    )
    resp = await client.post(
        "/api/auth/register",
        json={
            "admin_name": "testadmin",
            "class_name": "TestClass",
            "student_id": "NAME001",
            "password": "p",
            "display_name": "Zhang San",
        },
    )
    assert resp.status_code == 201
    # Verify display_name is stored and returned
    data = resp.json()
    assert data.get("display_name") == "Zhang San"


# ============================================================================
# 1.2 Login
# ============================================================================


async def test_login_admin_success(client: AsyncClient, admin_token: str):
    """#8 — Admin logs in successfully."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "adminpass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "admin"


async def test_login_super_admin_success(
    client: AsyncClient, super_admin_token: str
):
    """#9 — Super admin logs in successfully."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "superadmin", "password": "superpass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "super_admin"
    assert "access_token" in data


async def test_login_student_single_class(
    client: AsyncClient, student_token: str
):
    """#10 — Student with one class logs in directly."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "STU001", "password": "stupass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["class_id"] is not None
    assert data["class_name"] is not None


async def test_login_student_multi_class_returns_selection(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    another_admin_with_class: tuple[str, str],
):
    """#11 — Student in multiple classes gets class selection."""
    token_a, class_id_a = admin_with_class
    token_b, class_id_b = another_admin_with_class

    # Add same student to both rosters
    for tok, cid in [(token_a, class_id_a), (token_b, class_id_b)]:
        await client.post(
            f"/api/admin/classes/{cid}/roster",
            json={"student_id": "MULTI_LOGIN"},
            headers=auth_header(tok),
        )

    # Register in first class
    await client.post(
        "/api/auth/register",
        json={
            "admin_name": "testadmin",
            "class_name": "TestClass",
            "student_id": "MULTI_LOGIN",
            "password": "mp",
        },
    )
    # Register in second class
    await client.post(
        "/api/auth/register",
        json={
            "admin_name": "otheradmin",
            "class_name": "OtherClass",
            "student_id": "MULTI_LOGIN",
            "password": "mp",
        },
    )

    resp = await client.post(
        "/api/auth/login",
        json={"username": "MULTI_LOGIN", "password": "mp"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("requires_class_selection") is True
    assert len(data["classes"]) == 2


async def test_login_wrong_password(client: AsyncClient, admin_token: str):
    """#12 — Wrong password."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "WRONG"},
    )
    assert resp.status_code == 401
    assert "用户名或密码错误" in resp.json()["detail"]


async def test_login_nonexistent_user(client: AsyncClient):
    """#13 — User does not exist."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "x"},
    )
    assert resp.status_code == 401
    assert "用户名或密码错误" in resp.json()["detail"]


async def test_login_disabled_admin(
    client: AsyncClient,
    super_admin_token: str,
    admin_token: str,
    db_session,
):
    """#14 — Disabled admin cannot use token on protected endpoints."""
    # Get admin id
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    admin_id = resp.json()["items"][0]["id"]

    # Disable admin
    await client.put(
        f"/api/super-admin/admins/{admin_id}/toggle-active",
        headers=auth_header(super_admin_token),
    )

    # Try to use admin token
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 403
    assert "账号已被禁用" in resp.json()["detail"]


# ============================================================================
# 1.3 Class Selection Login
# ============================================================================


async def test_select_class_login_success(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    another_admin_with_class: tuple[str, str],
):
    """#15 — Multi-class student selects a class and logs in."""
    token_a, class_id_a = admin_with_class
    token_b, class_id_b = another_admin_with_class

    for tok, cid in [(token_a, class_id_a), (token_b, class_id_b)]:
        await client.post(
            f"/api/admin/classes/{cid}/roster",
            json={"student_id": "SEL001"},
            headers=auth_header(tok),
        )

    await client.post(
        "/api/auth/register",
        json={
            "admin_name": "testadmin",
            "class_name": "TestClass",
            "student_id": "SEL001",
            "password": "sp",
        },
    )
    await client.post(
        "/api/auth/register",
        json={
            "admin_name": "otheradmin",
            "class_name": "OtherClass",
            "student_id": "SEL001",
            "password": "sp",
        },
    )

    resp = await client.post(
        "/api/auth/login/select-class",
        json={
            "username": "SEL001",
            "password": "sp",
            "class_id": class_id_a,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["class_id"] == class_id_a


async def test_select_class_login_wrong_class(
    client: AsyncClient, student_token: str
):
    """#16 — Select a class the student does not belong to."""
    fake_class_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/auth/login/select-class",
        json={
            "username": "STU001",
            "password": "stupass",
            "class_id": fake_class_id,
        },
    )
    assert resp.status_code == 401


# ============================================================================
# 1.4 Token & Permission Interception
# ============================================================================


async def test_access_without_token(client: AsyncClient):
    """#17 — No token on protected endpoint."""
    resp = await client.get("/api/admin/classes")
    assert resp.status_code in (401, 403)


async def test_access_with_invalid_token(client: AsyncClient):
    """#18 — Forged / invalid token."""
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header("invalid.token.here"),
    )
    assert resp.status_code in (401, 403)


async def test_student_cannot_access_admin_endpoint(
    client: AsyncClient, student_token: str
):
    """#19 — Student token on admin endpoint."""
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(student_token),
    )
    assert resp.status_code == 403
    assert "需要管理员权限" in resp.json()["detail"]


async def test_admin_cannot_access_super_admin_endpoint(
    client: AsyncClient, admin_token: str
):
    """#20 — Admin token on super_admin endpoint."""
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 403
    assert "需要超级管理员权限" in resp.json()["detail"]


async def test_admin_cannot_access_student_endpoint(
    client: AsyncClient, admin_token: str
):
    """#21 — Admin token on student endpoint."""
    resp = await client.get(
        "/api/submissions/my",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 403
    assert "需要学生权限" in resp.json()["detail"]


async def test_disabled_user_token_rejected(
    client: AsyncClient,
    super_admin_token: str,
    admin_token: str,
):
    """#22 — Disabled user's valid token is rejected."""
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    admin_id = resp.json()["items"][0]["id"]

    await client.put(
        f"/api/super-admin/admins/{admin_id}/toggle-active",
        headers=auth_header(super_admin_token),
    )

    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 403
    assert "账号已被禁用" in resp.json()["detail"]


# ============================================================================
# 1.5 Student Join New Class
# ============================================================================


@pytest.mark.xfail(reason="功能未实现: 学生加入新班级")
async def test_student_join_new_class_success(
    client: AsyncClient, student_token: str
):
    """#23 — Registered student joins a new class."""
    resp = await client.post(
        "/api/auth/join-class",
        json={"admin_name": "otheradmin", "class_name": "OtherClass"},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 200


@pytest.mark.xfail(reason="功能未实现: 学生加入新班级")
async def test_student_join_class_already_member(
    client: AsyncClient, student_token: str
):
    """#24 — Student already in target class."""
    resp = await client.post(
        "/api/auth/join-class",
        json={"admin_name": "testadmin", "class_name": "TestClass"},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400


@pytest.mark.xfail(reason="功能未实现: 学生加入新班级")
async def test_student_join_class_not_in_roster(
    client: AsyncClient, student_token: str
):
    """#25 — Student not in target class roster."""
    resp = await client.post(
        "/api/auth/join-class",
        json={"admin_name": "otheradmin", "class_name": "SomeClass"},
        headers=auth_header(student_token),
    )
    assert resp.status_code == 400
