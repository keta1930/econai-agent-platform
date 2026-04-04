import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from minio.error import S3Error
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import BACKUP_RETENTION_DAYS, MAX_BACKUPS_PER_ADMIN
from models.backup import Backup
from models.class_ import Class
from models.model_config import ModelConfig
from models.roster import StudentRoster
from models.sharing import SharingTopic, TopicVote
from models.submission import Submission
from models.task import Task
from models.user import User
from services.storage import storage_service
from utils import uuid7

logger = logging.getLogger(__name__)

BACKUPS_BUCKET = "backups"


# ── Startup ──────────────────────────────────────────────────────────────────


async def init_backups_bucket() -> None:
    """Create backups bucket and set lifecycle policy. Called at startup."""
    await asyncio.to_thread(storage_service.ensure_bucket_with_name, BACKUPS_BUCKET)
    await asyncio.to_thread(
        storage_service.set_bucket_lifecycle, BACKUPS_BUCKET, BACKUP_RETENTION_DAYS,
    )
    logger.info(
        "Backups bucket ready (retention=%d days)", BACKUP_RETENTION_DAYS,
    )


# ── Serialization helpers ────────────────────────────────────────────────────


def _serialize_value(value: object) -> object:
    """Convert a single value for JSON serialization."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _row_to_dict(row: object) -> dict:
    """Convert a SQLAlchemy ORM instance to a plain dict with JSON-safe values."""
    mapper = type(row).__mapper__  # type: ignore[attr-defined]
    return {
        col.key: _serialize_value(getattr(row, col.key))
        for col in mapper.column_attrs
    }


# ── Data export ──────────────────────────────────────────────────────────────


async def export_admin_data(
    db: AsyncSession, admin_id: uuid.UUID, admin_username: str,
) -> bytes:
    """Export all data belonging to an admin as JSON bytes.

    Query chain:
      classes (created_by) → student_roster, users, tasks, sharing_topics (class_id)
      → submissions (task_id), topic_votes (topic_id)
      + model_configs (admin_id)
    """
    # 1. Classes
    classes = (
        await db.execute(select(Class).where(Class.created_by == admin_id))
    ).scalars().all()
    class_ids = [c.id for c in classes]

    # Short-circuit: if no classes, still export empty data + model_configs
    if class_ids:
        # 2. Student roster
        roster = (
            await db.execute(
                select(StudentRoster).where(StudentRoster.class_id.in_(class_ids))
            )
        ).scalars().all()

        # 3. Student users
        users = (
            await db.execute(
                select(User).where(User.class_id.in_(class_ids), User.role == "student")
            )
        ).scalars().all()

        # 4. Tasks
        tasks = (
            await db.execute(select(Task).where(Task.class_id.in_(class_ids)))
        ).scalars().all()
        task_ids = [t.id for t in tasks]

        # 5. Submissions
        submissions = (
            await db.execute(
                select(Submission).where(Submission.task_id.in_(task_ids))
            )
        ).scalars().all() if task_ids else []

        # 7. Sharing topics
        topics = (
            await db.execute(
                select(SharingTopic).where(SharingTopic.class_id.in_(class_ids))
            )
        ).scalars().all()
        topic_ids = [t.id for t in topics]

        # 8. Topic votes
        votes = (
            await db.execute(
                select(TopicVote).where(TopicVote.topic_id.in_(topic_ids))
            )
        ).scalars().all() if topic_ids else []
    else:
        roster = []
        users = []
        tasks = []
        submissions = []
        topics = []
        votes = []

    # 6. Model configs (independent of classes)
    model_configs = (
        await db.execute(
            select(ModelConfig).where(ModelConfig.admin_id == admin_id)
        )
    ).scalars().all()

    payload = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "admin": {
            "id": str(admin_id),
            "username": admin_username,
        },
        "data": {
            "classes": [_row_to_dict(r) for r in classes],
            "student_roster": [_row_to_dict(r) for r in roster],
            "users": [_row_to_dict(r) for r in users],
            "tasks": [_row_to_dict(r) for r in tasks],
            "submissions": [_row_to_dict(r) for r in submissions],
            "model_configs": [_row_to_dict(r) for r in model_configs],
            "sharing_topics": [_row_to_dict(r) for r in topics],
            "topic_votes": [_row_to_dict(r) for r in votes],
        },
    }

    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


# ── CRUD operations ──────────────────────────────────────────────────────────


async def create_backup(
    db: AsyncSession, admin: User, display_name: str | None,
) -> Backup:
    """Create a new backup for the given admin.

    Raises ValueError if backup limit is reached.
    """
    count_result = await db.execute(
        select(func.count()).select_from(Backup).where(Backup.admin_id == admin.id)
    )
    count = count_result.scalar_one()

    if count >= MAX_BACKUPS_PER_ADMIN:
        raise ValueError(
            f"已达备份上限（{MAX_BACKUPS_PER_ADMIN}），请删除旧备份后重试"
        )

    if not display_name:
        display_name = f"备份_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    data = await export_admin_data(db, admin.id, admin.username)

    object_key = f"{admin.id}/{uuid7()}.json"
    await asyncio.to_thread(
        storage_service.put_object_to_bucket,
        BACKUPS_BUCKET, object_key, data, "application/json",
    )

    backup = Backup(
        admin_id=admin.id,
        display_name=display_name,
        object_key=object_key,
        size=len(data),
    )
    db.add(backup)
    await db.commit()
    await db.refresh(backup)

    logger.info("Backup created: %s (%d bytes) for admin %s", object_key, len(data), admin.id)
    return backup


async def list_backups(db: AsyncSession, admin_id: uuid.UUID) -> list[Backup]:
    """List backups for an admin, cleaning up orphaned DB records."""
    result = await db.execute(
        select(Backup)
        .where(Backup.admin_id == admin_id)
        .order_by(Backup.created_at.desc())
    )
    all_backups = list(result.scalars().all())

    valid: list[Backup] = []
    for backup in all_backups:
        exists = await _minio_object_exists(backup.object_key)
        if exists:
            valid.append(backup)
        else:
            logger.info("Cleaning orphaned backup record: %s", backup.object_key)
            await db.delete(backup)

    if len(valid) != len(all_backups):
        await db.commit()

    return valid


async def get_backup_download_url(
    db: AsyncSession, backup_id: uuid.UUID, admin_id: uuid.UUID,
) -> tuple[str, str]:
    """Get a presigned download URL for a backup.

    Returns (url, suggested_filename).
    Raises ValueError if not found.
    """
    backup = await _get_backup_or_raise(db, backup_id, admin_id)

    url = await asyncio.to_thread(
        storage_service.presigned_get_url_from_bucket,
        BACKUPS_BUCKET, backup.object_key,
    )
    return url, f"{backup.display_name}.json"


async def rename_backup(
    db: AsyncSession, backup_id: uuid.UUID, admin_id: uuid.UUID, display_name: str,
) -> Backup:
    """Rename a backup's display name.

    Raises ValueError if not found.
    """
    backup = await _get_backup_or_raise(db, backup_id, admin_id)
    backup.display_name = display_name
    await db.commit()
    await db.refresh(backup)
    return backup


async def delete_backup(
    db: AsyncSession, backup_id: uuid.UUID, admin_id: uuid.UUID,
) -> None:
    """Delete a backup (MinIO file + DB record).

    Raises ValueError if not found.
    """
    backup = await _get_backup_or_raise(db, backup_id, admin_id)

    # Delete MinIO file first; ignore if already gone (lifecycle expiry)
    try:
        await asyncio.to_thread(
            storage_service.remove_object_from_bucket,
            BACKUPS_BUCKET, backup.object_key,
        )
    except S3Error as e:
        if e.code != "NoSuchKey":
            raise

    await db.delete(backup)
    await db.commit()
    logger.info("Backup deleted: %s", backup.object_key)


# ── Private helpers ──────────────────────────────────────────────────────────


async def _get_backup_or_raise(
    db: AsyncSession, backup_id: uuid.UUID, admin_id: uuid.UUID,
) -> Backup:
    """Fetch a backup by id and admin, or raise ValueError."""
    result = await db.execute(
        select(Backup).where(Backup.id == backup_id, Backup.admin_id == admin_id)
    )
    backup = result.scalar_one_or_none()
    if not backup:
        raise ValueError("备份不存在")
    return backup


async def _minio_object_exists(object_key: str) -> bool:
    """Check whether an object exists in the backups bucket."""
    try:
        await asyncio.to_thread(
            storage_service.client.stat_object, BACKUPS_BUCKET, object_key,
        )
        return True
    except S3Error as e:
        if e.code == "NoSuchKey":
            return False
        raise
