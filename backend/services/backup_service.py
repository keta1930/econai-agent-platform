import asyncio
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from config import DATABASE_URL, BACKUP_RETENTION_DAYS, PG_CONTAINER_NAME
from schemas.backup import BackupInfo
from services.storage import storage_service

logger = logging.getLogger(__name__)

BACKUPS_BUCKET = "backups"


def _build_docker_pg_dump_cmd() -> tuple[list[str], dict[str, str]]:
    """Build a docker exec command to run pg_dump inside the postgres container.

    Returns (cmd_args, env). pg_dump runs inside the container so the host
    doesn't need PostgreSQL client tools installed.
    """
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(url)

    username = parsed.username or "postgres"
    dbname = parsed.path.lstrip("/") or "postgres"

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = [
        "docker", "exec",
        "-e", f"PGPASSWORD={parsed.password or ''}",
        PG_CONTAINER_NAME,
        "pg_dump", "--format=custom",
        "--username", username,
        "--dbname", dbname,
    ]
    return cmd, env


async def init_backups_bucket() -> None:
    """Create backups bucket and set lifecycle policy. Called at startup."""
    await asyncio.to_thread(storage_service.ensure_bucket_with_name, BACKUPS_BUCKET)
    await asyncio.to_thread(
        storage_service.set_bucket_lifecycle, BACKUPS_BUCKET, BACKUP_RETENTION_DAYS,
    )
    logger.info(
        "Backups bucket ready (retention=%d days)", BACKUP_RETENTION_DAYS,
    )


async def create_backup() -> BackupInfo:
    """Execute pg_dump and upload the result to MinIO."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.sql"
    cmd, env = _build_docker_pg_dump_cmd()

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_msg = stderr.decode().strip()
        logger.error("pg_dump failed: %s", error_msg)
        raise RuntimeError(f"pg_dump failed: {error_msg}")

    await asyncio.to_thread(
        storage_service.put_object_to_bucket,
        BACKUPS_BUCKET, filename, stdout, "application/octet-stream",
    )

    logger.info("Backup created: %s (%d bytes)", filename, len(stdout))
    return BackupInfo(
        filename=filename,
        size=len(stdout),
        created_at=datetime.now(timezone.utc),
    )


async def list_backups() -> list[BackupInfo]:
    """List all backups from MinIO, sorted by creation time descending."""
    objects = await asyncio.to_thread(
        storage_service.list_objects_in_bucket, BACKUPS_BUCKET,
    )
    items = [
        BackupInfo(
            filename=obj.object_name,
            size=obj.size,
            created_at=obj.last_modified,
        )
        for obj in objects
        if not obj.is_dir
    ]
    items.sort(key=lambda b: b.created_at, reverse=True)
    return items


async def get_backup_download_url(filename: str) -> str:
    """Generate a presigned download URL for a backup file."""
    return await asyncio.to_thread(
        storage_service.presigned_get_url_from_bucket, BACKUPS_BUCKET, filename,
    )


async def delete_backup(filename: str) -> None:
    """Delete a backup file from MinIO."""
    await asyncio.to_thread(
        storage_service.remove_object_from_bucket, BACKUPS_BUCKET, filename,
    )
    logger.info("Backup deleted: %s", filename)
