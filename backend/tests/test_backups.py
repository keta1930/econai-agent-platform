"""Tests for backup management (8 cases)."""

import uuid
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


def _mock_backup_storage():
    """Patch MinIO operations used by backup_service."""
    return patch.multiple(
        "services.storage.storage_service",
        put_object_to_bucket=lambda *a, **kw: None,
        presigned_get_url_from_bucket=lambda *a, **kw: "https://download.url/backup",
        remove_object_from_bucket=lambda *a, **kw: None,
        client=MagicMock(
            stat_object=MagicMock(return_value=True),
        ),
    )


async def _create_backup(
    client: AsyncClient, token: str, display_name: str | None = None
) -> dict:
    """Helper: create a backup."""
    body = {"display_name": display_name} if display_name else None
    with _mock_backup_storage():
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

    with _mock_backup_storage():
        resp = await client.get(
            "/api/admin/backups", headers=auth_header(admin_token)
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1


async def test_admin_download_backup(
    client: AsyncClient, admin_token: str
):
    """#121 — Get backup download URL."""
    backup = await _create_backup(client, admin_token)

    with _mock_backup_storage():
        resp = await client.get(
            f"/api/admin/backups/{backup['id']}/download",
            headers=auth_header(admin_token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "download_url" in data
    assert "filename" in data


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

    with _mock_backup_storage():
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
