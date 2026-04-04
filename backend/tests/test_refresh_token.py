"""Tests for dual-token authentication (12 cases)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_header, _create_user_in_db, _login_full


async def test_login_returns_both_tokens(client: AsyncClient, admin_token: str):
    """#1 — Login returns both access_token and refresh_token."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "adminpass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert len(data["access_token"]) > 0
    assert len(data["refresh_token"]) > 0


async def test_access_token_works(client: AsyncClient, admin_token: str):
    """#2 — Access token grants access to protected endpoints."""
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200


async def test_expired_access_token_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    """#3 — Expired access token is rejected."""
    import jwt as pyjwt
    from config import SECRET_KEY

    user = await _create_user_in_db(
        db_session, username="exptest", password="pass", role="admin"
    )

    # Manually craft a token with past expiration
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "class_id": None,
        "exp": datetime.now(timezone.utc) - timedelta(seconds=10),
    }
    token = pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")

    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(token),
    )
    assert resp.status_code == 401


async def test_refresh_yields_new_access_token(
    client: AsyncClient, admin_token: str
):
    """#4 — Refresh token yields a new valid access token."""
    login_data = await _login_full(client, "testadmin", "adminpass")
    refresh_token = login_data["refresh_token"]

    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    new_access = resp.json()["access_token"]
    assert len(new_access) > 0

    # New access token should work
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(new_access),
    )
    assert resp.status_code == 200


async def test_invalid_refresh_token(client: AsyncClient):
    """#5 — Invalid refresh token is rejected."""
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": "completely-invalid-token"},
    )
    assert resp.status_code == 401


async def test_expired_refresh_token(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """#6 — Expired refresh token is rejected."""
    login_data = await _login_full(client, "testadmin", "adminpass")
    refresh_token = login_data["refresh_token"]

    # Manually expire the refresh token in DB
    from models.refresh_token import RefreshToken
    from auth.jwt import hash_refresh_token

    token_hash = hash_refresh_token(refresh_token)
    await db_session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
    )
    await db_session.commit()

    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 401
    assert "过期" in resp.json()["detail"]


async def test_disabled_user_refresh_rejected(
    client: AsyncClient, super_admin_token: str, admin_token: str
):
    """#7 — Disabled user cannot refresh."""
    login_data = await _login_full(client, "testadmin", "adminpass")
    refresh_token = login_data["refresh_token"]

    # Get admin id and disable
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    admin_id = resp.json()["items"][0]["id"]
    await client.put(
        f"/api/super-admin/admins/{admin_id}/toggle-active",
        headers=auth_header(super_admin_token),
    )

    # Refresh should fail (tokens revoked on disable)
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 401


async def test_disabled_user_access_token_still_valid(
    client: AsyncClient, super_admin_token: str, admin_token: str
):
    """#8 — Disabled user's existing access token remains valid (stateless design)."""
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    admin_id = resp.json()["items"][0]["id"]
    await client.put(
        f"/api/super-admin/admins/{admin_id}/toggle-active",
        headers=auth_header(super_admin_token),
    )

    # Access token still works
    resp = await client.get(
        "/api/admin/classes",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200


async def test_multi_device_independent_refresh_tokens(
    client: AsyncClient, admin_token: str
):
    """#9 — Multiple logins produce independent refresh tokens."""
    login1 = await _login_full(client, "testadmin", "adminpass")
    login2 = await _login_full(client, "testadmin", "adminpass")

    assert login1["refresh_token"] != login2["refresh_token"]

    # Both should work for refresh
    for rt in [login1["refresh_token"], login2["refresh_token"]]:
        resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": rt}
        )
        assert resp.status_code == 200


async def test_logout_deletes_refresh_token(
    client: AsyncClient, admin_token: str
):
    """#10 — Logout invalidates the specific refresh token."""
    login1 = await _login_full(client, "testadmin", "adminpass")
    login2 = await _login_full(client, "testadmin", "adminpass")

    # Logout device 1
    resp = await client.post(
        "/api/auth/logout",
        json={"refresh_token": login1["refresh_token"]},
    )
    assert resp.status_code == 204

    # Device 1 refresh should fail
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": login1["refresh_token"]},
    )
    assert resp.status_code == 401

    # Device 2 refresh should still work
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": login2["refresh_token"]},
    )
    assert resp.status_code == 200


async def test_cascade_delete_user_removes_tokens(
    client: AsyncClient,
    super_admin_token: str,
    admin_token: str,
    db_session: AsyncSession,
):
    """#11 — Deleting a user cascades to their refresh tokens."""
    login_data = await _login_full(client, "testadmin", "adminpass")
    refresh_token = login_data["refresh_token"]

    # Get admin id
    resp = await client.get(
        "/api/super-admin/admins",
        headers=auth_header(super_admin_token),
    )
    admin_id = resp.json()["items"][0]["id"]

    # Delete admin
    resp = await client.delete(
        f"/api/super-admin/admins/{admin_id}",
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 204

    # Verify token no longer works for refresh
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 401


async def test_refresh_cleans_expired_tokens(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """#12 — Refreshing cleans up expired tokens for the same user."""
    from models.refresh_token import RefreshToken
    from auth.jwt import hash_refresh_token

    # Create two sessions
    login1 = await _login_full(client, "testadmin", "adminpass")
    login2 = await _login_full(client, "testadmin", "adminpass")

    # Manually expire login1's token
    token_hash = hash_refresh_token(login1["refresh_token"])
    await db_session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
    )
    await db_session.commit()

    # Count tokens before refresh
    from auth.jwt import decode_access_token
    payload = decode_access_token(login2["access_token"])
    user_id = payload["sub"]
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == uuid.UUID(user_id))
    )
    count_before = len(result.scalars().all())

    # Refresh with login2 should trigger cleanup
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": login2["refresh_token"]},
    )
    assert resp.status_code == 200

    # Expired token should be cleaned up
    db_session.expire_all()
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == uuid.UUID(user_id))
    )
    count_after = len(result.scalars().all())
    assert count_after < count_before
