"""Tests for backup management (8 cases)."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header

# All tests use the _backup_dir fixture which patches BACKUP_DIR
# to a per-test temp directory. No mocking of file ops needed —
# backup_service writes real files to the temp dir.

pytestmark = pytest.mark.usefixtures("_backup_dir")


@pytest.fixture
def _backup_dir(tmp_path, monkeypatch):
    """Point BACKUP_DIR to a per-test temp directory."""
    monkeypatch.setattr("services.backup_service.BACKUP_DIR", str(tmp_path))


async def _create_backup(
    client: AsyncClient, token: str, display_name: str | None = None
) -> dict:
    """Helper: create a backup."""
    body = {"display_name": display_name} if display_name else None
    resp = await client.post(
        "/api/admin/backups",
        json=body,
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    return resp.json()


async def test_admin_create_backup(
    client: AsyncClient, admin_token: str
):
    """#118 — Create a backup."""
    data = await _create_backup(client, admin_token)
    assert "id" in data
    assert "display_name" in data
    assert "size" in data


async def test_admin_create_backup_with_name(
    client: AsyncClient, admin_token: str
):
    """#119 — Create backup with custom display_name."""
    data = await _create_backup(client, admin_token, "My Backup")
    assert data["display_name"] == "My Backup"


async def test_admin_list_backups(
    client: AsyncClient, admin_token: str
):
    """#120 — List backups."""
    await _create_backup(client, admin_token)

    resp = await client.get(
        "/api/admin/backups", headers=auth_header(admin_token)
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1


async def test_admin_download_backup(
    client: AsyncClient, admin_token: str
):
    """#121 — Download backup file."""
    backup = await _create_backup(client, admin_token)

    resp = await client.get(
        f"/api/admin/backups/{backup['id']}/download",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json; charset=utf-8"
    # Body should be valid JSON with the export structure
    data = resp.json()
    assert "version" in data
    assert "data" in data
    # password_hash must not appear in exported users
    for user in data["data"].get("users", []):
        assert "password_hash" not in user


async def test_admin_download_nonexistent_backup(
    client: AsyncClient, admin_token: str
):
    """#122 — Download nonexistent backup."""
    resp = await client.get(
        f"/api/admin/backups/{uuid.uuid4()}/download",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


async def test_admin_rename_backup(
    client: AsyncClient, admin_token: str
):
    """#123 — Rename a backup."""
    backup = await _create_backup(client, admin_token, "Old Name")

    resp = await client.patch(
        f"/api/admin/backups/{backup['id']}",
        json={"display_name": "New Name"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New Name"


async def test_admin_delete_backup(
    client: AsyncClient, admin_token: str
):
    """#124 — Delete a backup."""
    backup = await _create_backup(client, admin_token)

    resp = await client.delete(
        f"/api/admin/backups/{backup['id']}",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 204


async def test_admin_delete_nonexistent_backup(
    client: AsyncClient, admin_token: str
):
    """#125 — Delete nonexistent backup."""
    resp = await client.delete(
        f"/api/admin/backups/{uuid.uuid4()}",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404
