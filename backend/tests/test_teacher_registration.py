"""Tests for teacher self-registration via invite code (8 cases)."""

from httpx import AsyncClient

from tests.conftest import auth_header, _create_invite_code


async def test_register_teacher_success(
    client: AsyncClient, super_admin_token: str
):
    """#1 — Teacher registers with a valid invite code and can log in immediately."""
    code = await _create_invite_code(client, super_admin_token, "注册测试")

    resp = await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": code,
            "username": "new_teacher",
            "password": "teacherpass",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "admin"
    assert "id" in data

    # Can log in immediately
    resp = await client.post(
        "/api/auth/login",
        json={"username": "new_teacher", "password": "teacherpass"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


async def test_register_teacher_invalid_code(
    client: AsyncClient,
):
    """#2 — Invalid invite code is rejected."""
    resp = await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": "totally_invalid_code_here",
            "username": "teacher_inv",
            "password": "pass",
        },
    )
    assert resp.status_code == 400
    assert "邀请码无效" in resp.json()["detail"]


async def test_register_teacher_deleted_code(
    client: AsyncClient, super_admin_token: str
):
    """#3 — Deleted invite code is rejected."""
    code = await _create_invite_code(client, super_admin_token, "删除码测试")

    # Get code id
    resp = await client.get(
        "/api/super-admin/invite-codes",
        headers=auth_header(super_admin_token),
    )
    items = [i for i in resp.json()["items"] if i["category"] == "删除码测试"]
    code_id = items[0]["id"]

    # Delete the code
    await client.delete(
        f"/api/super-admin/invite-codes/{code_id}",
        headers=auth_header(super_admin_token),
    )

    # Try registering
    resp = await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": code,
            "username": "teacher_del_code",
            "password": "pass",
        },
    )
    assert resp.status_code == 400
    assert "邀请码无效" in resp.json()["detail"]


async def test_register_teacher_old_code_after_regenerate(
    client: AsyncClient, super_admin_token: str
):
    """#4 — Old invite code after regeneration is rejected."""
    old_code = await _create_invite_code(client, super_admin_token, "旧码测试")

    # Get code id
    resp = await client.get(
        "/api/super-admin/invite-codes",
        headers=auth_header(super_admin_token),
    )
    items = [i for i in resp.json()["items"] if i["category"] == "旧码测试"]
    code_id = items[0]["id"]

    # Regenerate
    await client.post(
        f"/api/super-admin/invite-codes/{code_id}/regenerate",
        headers=auth_header(super_admin_token),
    )

    # Old code should fail
    resp = await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": old_code,
            "username": "teacher_old",
            "password": "pass",
        },
    )
    assert resp.status_code == 400
    assert "邀请码无效" in resp.json()["detail"]


async def test_register_teacher_duplicate_username(
    client: AsyncClient, super_admin_token: str
):
    """#5 — Duplicate username among admins is rejected."""
    code = await _create_invite_code(client, super_admin_token, "重名测试")

    # Register first teacher
    resp = await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": code,
            "username": "dup_teacher",
            "password": "pass1",
        },
    )
    assert resp.status_code == 201

    # Try the same username again
    resp = await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": code,
            "username": "dup_teacher",
            "password": "pass2",
        },
    )
    assert resp.status_code == 400
    assert "用户名已存在，请联系管理员。" in resp.json()["detail"]


async def test_register_teacher_multiple_with_same_code(
    client: AsyncClient, super_admin_token: str
):
    """#6 — Multiple teachers can register with the same invite code."""
    code = await _create_invite_code(client, super_admin_token, "多人同码")

    for i in range(3):
        resp = await client.post(
            "/api/auth/register-teacher",
            json={
                "invite_code": code,
                "username": f"multi_teacher_{i}",
                "password": "pass",
            },
        )
        assert resp.status_code == 201


async def test_register_teacher_category_shown_in_admin_list(
    client: AsyncClient, super_admin_token: str
):
    """#7 — Super admin list shows correct category for registered teacher."""
    code = await _create_invite_code(client, super_admin_token, "分类展示")

    await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": code,
            "username": "cat_teacher",
            "password": "pass",
        },
    )

    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    items = resp.json()["items"]
    teacher = next(i for i in items if i["username"] == "cat_teacher")
    assert teacher["category"] == "分类展示"


async def test_register_teacher_category_null_after_code_deleted(
    client: AsyncClient, super_admin_token: str
):
    """#8 — After deleting invite code, teacher's category becomes null."""
    code = await _create_invite_code(client, super_admin_token, "分类清空")

    await client.post(
        "/api/auth/register-teacher",
        json={
            "invite_code": code,
            "username": "null_cat_teacher",
            "password": "pass",
        },
    )

    # Get invite code id
    resp = await client.get(
        "/api/super-admin/invite-codes",
        headers=auth_header(super_admin_token),
    )
    items = [i for i in resp.json()["items"] if i["category"] == "分类清空"]
    code_id = items[0]["id"]

    # Delete the invite code
    await client.delete(
        f"/api/super-admin/invite-codes/{code_id}",
        headers=auth_header(super_admin_token),
    )

    # Check admin list — category should be null
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    teacher = next(
        i for i in resp.json()["items"] if i["username"] == "null_cat_teacher"
    )
    assert teacher["category"] is None
