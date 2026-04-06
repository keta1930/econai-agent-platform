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


# ── 启动 ─────────────────────────────────────────────────────────────────────


async def init_backups_dir() -> None:
    """确保备份目录存在。启动时调用。"""
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("备份目录就绪 — 路径=%s", BACKUP_DIR)


# ── 序列化辅助 ────────────────────────────────────────────────────────────────


def _serialize_value(value: object) -> object:
    """将单个值转换为 JSON 可序列化格式。"""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


_EXCLUDED_COLUMNS = frozenset({"password_hash"})


def _row_to_dict(row: object) -> dict:
    """将 SQLAlchemy ORM 实例转换为 JSON 安全的纯字典。"""
    mapper = type(row).__mapper__  # type: ignore[attr-defined]
    return {
        col.key: _serialize_value(getattr(row, col.key))
        for col in mapper.column_attrs
        if col.key not in _EXCLUDED_COLUMNS
    }


# ── 数据导出 ──────────────────────────────────────────────────────────────────


async def export_admin_data(
    db: AsyncSession, admin_id: uuid.UUID, admin_username: str,
) -> bytes:
    """将管理员的所有数据导出为 JSON 字节。

    查询链：
      classes (created_by) -> student_roster, users, tasks, sharing_topics (class_id)
      -> submissions (task_id), topic_votes (topic_id)
      + model_configs (admin_id)
    """
    # 1. 班级
    classes = (
        await db.execute(select(Class).where(Class.created_by == admin_id))
    ).scalars().all()
    class_ids = [c.id for c in classes]

    # 短路：无班级时仍导出空数据 + model_configs
    if class_ids:
        # 2. 学生名单
        roster = (
            await db.execute(
                select(StudentRoster).where(StudentRoster.class_id.in_(class_ids))
            )
        ).scalars().all()

        # 3. 学生用户（通过 class_members 关联）
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

        # 4. 作业
        tasks = (
            await db.execute(select(Task).where(Task.class_id.in_(class_ids)))
        ).scalars().all()
        task_ids = [t.id for t in tasks]

        # 5. 提交
        submissions = (
            await db.execute(
                select(Submission).where(Submission.task_id.in_(task_ids))
            )
        ).scalars().all() if task_ids else []

        # 7. 分享主题
        topics = (
            await db.execute(
                select(SharingTopic).where(SharingTopic.class_id.in_(class_ids))
            )
        ).scalars().all()
        topic_ids = [t.id for t in topics]

        # 8. 投票
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

    # 6. 模型配置（独立于班级）
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


# ── CRUD 操作 ─────────────────────────────────────────────────────────────────


async def create_backup(
    db: AsyncSession, admin_id: uuid.UUID, display_name: str | None,
) -> Backup:
    """为指定管理员创建新备份。

    达到备份上限时抛出 ValueError。
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

    # 获取管理员用户名用于导出元数据
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

    logger.info("备份创建完成 — 路径=%s, 大小=%d, 管理员=%s", object_key, len(data), admin_id)
    return backup


async def list_backups(db: AsyncSession, admin_id: uuid.UUID) -> list[Backup]:
    """列出管理员的备份，同时清理孤立的数据库记录。"""
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
            logger.info("清理孤立备份记录 — 路径=%s", backup.object_key)
            await db.delete(backup)

    if len(valid) != len(all_backups):
        await db.commit()

    return valid


async def get_backup_file_path(
    db: AsyncSession, backup_id: uuid.UUID, admin_id: uuid.UUID,
) -> tuple[Path, str]:
    """获取备份文件路径。

    返回 (file_path, suggested_filename)。
    找不到或文件缺失时抛出 ValueError。
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
    """重命名备份的显示名称。

    找不到时抛出 ValueError。
    """
    backup = await _get_backup_or_raise(db, backup_id, admin_id)
    backup.display_name = display_name
    await db.commit()
    await db.refresh(backup)
    return backup


async def delete_backup(
    db: AsyncSession, backup_id: uuid.UUID, admin_id: uuid.UUID,
) -> None:
    """删除备份（本地文件 + 数据库记录）。

    找不到时抛出 ValueError。
    """
    backup = await _get_backup_or_raise(db, backup_id, admin_id)

    file_path = Path(BACKUP_DIR) / backup.object_key
    if file_path.exists():
        file_path.unlink()

    await db.delete(backup)
    await db.commit()
    logger.info("备份已删除 — 路径=%s", backup.object_key)


# ── 私有辅助 ──────────────────────────────────────────────────────────────────


async def _get_backup_or_raise(
    db: AsyncSession, backup_id: uuid.UUID, admin_id: uuid.UUID,
) -> Backup:
    """按 id 和管理员获取备份，找不到则抛出 ValueError。"""
    result = await db.execute(
        select(Backup).where(Backup.id == backup_id, Backup.admin_id == admin_id)
    )
    backup = result.scalar_one_or_none()
    if not backup:
        raise ValueError("备份不存在")
    return backup
