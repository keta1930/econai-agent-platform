import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import BACKUP_DIR, MAX_BACKUPS_PER_ADMIN
from models.backup import Backup
from models.class_ import Class
from models.model_config import ModelConfig
from models.roster import StudentRoster
from models.sharing import SharingTopic, TopicVote
from models.submission import Submission
from models.task import Task
from models.class_member import ClassMember
from models.user import User
from utils import uuid7

logger = logging.getLogger(__name__)


# ── Startup ──────────────────────────────────────────────────────────────────


async def init_backups_dir() -> None:
    """Ensure backup directory exists. Called at startup."""
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Backup directory ready: %s", BACKUP_DIR)


# ── Serialization helpers ────────────────────────────────────────────────────


def _serialize_value(value: object) -> object:
    """Convert a single value for JSON serialization."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


_EXCLUDED_COLUMNS = frozenset({"password_hash"})


def _row_to_dict(row: object) -> dict:
    """Convert a SQLAlchemy ORM instance to a plain dict with JSON-safe values."""
    mapper = type(row).__mapper__  # type: ignore[attr-defined]
    return {
        col.key: _serialize_value(getattr(row, col.key))
        for col in mapper.column_attrs
        if col.key not in _EXCLUDED_COLUMNS
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

        # 3. Student users (via class_members join)
        student_ids_stmt = (
            select(ClassMember.user_id)
            .where(ClassMember.class_id.in_(class_ids))
        )
        users = (
            await db.execute(
                select(User).where(
                    User.id.in_(student_ids_stmt),
                    User.role == "student",
                )
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
    db: AsyncSession, admin_id: uuid.UUID, display_name: str | None,
) -> Backup:
    """Create a new backup for the given admin.

    Raises ValueError if backup limit is reached.
    """
    count_result = await db.execute(
        select(func.count()).select_from(Backup).where(Backup.admin_id == admin_id)
    )
    count = count_result.scalar_one()

    if count >= MAX_BACKUPS_PER_ADMIN:
        raise ValueError(
            f"已达备份上限（{MAX_BACKUPS_PER_ADMIN}），请删除旧备份后重试"
        )

    if not display_name:
        display_name = f"备份_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # Fetch admin username for export metadata
    admin_result = await db.execute(select(User).where(User.id == admin_id))
    admin_user = admin_result.scalar_one()

    data = await export_admin_data(db, admin_id, admin_user.username)

    object_key = f"{admin_id}/{uuid7()}.json"
    file_path = Path(BACKUP_DIR) / object_key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(file_path.write_bytes, data)

    backup = Backup(
        admin_id=admin_id,
        display_name=display_name,
        object_key=object_key,
        size=len(data),
    )
    db.add(backup)
    await db.commit()
    await db.refresh(backup)

    logger.info("Backup created: %s (%d bytes) for admin %s", object_key, len(data), admin_id)
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
        file_path = Path(BACKUP_DIR) / backup.object_key
        if file_path.exists():
            valid.append(backup)
        else:
            logger.info("Cleaning orphaned backup record: %s", backup.object_key)
            await db.delete(backup)

    if len(valid) != len(all_backups):
        await db.commit()

    return valid


async def get_backup_file_path(
    db: AsyncSession, backup_id: uuid.UUID, admin_id: uuid.UUID,
) -> tuple[Path, str]:
    """Get the file path for a backup.

    Returns (file_path, suggested_filename).
    Raises ValueError if not found or file missing.
    """
    backup = await _get_backup_or_raise(db, backup_id, admin_id)
    file_path = (Path(BACKUP_DIR) / backup.object_key).resolve()
    if not str(file_path).startswith(str(Path(BACKUP_DIR).resolve())):
        raise ValueError("非法路径")
    if not file_path.exists():
        raise ValueError("备份文件不存在")
    return file_path, f"{backup.display_name}.json"


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
    """Delete a backup (local file + DB record).

    Raises ValueError if not found.
    """
    backup = await _get_backup_or_raise(db, backup_id, admin_id)

    file_path = Path(BACKUP_DIR) / backup.object_key
    if file_path.exists():
        file_path.unlink()

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
