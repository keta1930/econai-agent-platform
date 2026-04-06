"""孤立账号清理服务。

定期删除无班级成员关系且创建超过 15 天的学生账号。
关联的 refresh_tokens 通过外键 CASCADE 自动清理。
"""

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

_scheduler = None

ORPHAN_RETENTION_DAYS = 15


async def cleanup_orphan_accounts(engine: AsyncEngine) -> int:
    """删除无班级成员关系且超过保留天数的学生账号。

    返回删除的账号数量。
    """
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=ORPHAN_RETENTION_DAYS)

        # 使用原生 SQL 单次高效 DELETE + 子查询
        result = await db.execute(
            text("""
                DELETE FROM users
                WHERE role = 'student'
                  AND created_at < :cutoff
                  AND id NOT IN (SELECT user_id FROM class_members)
            """),
            {"cutoff": cutoff},
        )
        deleted = result.rowcount
        await db.commit()

    if deleted > 0:
        logger.info("孤立账号清理完成 — 删除=%d", deleted)
    return deleted


def start_cleanup_scheduler(engine: AsyncEngine) -> None:
    """启动 APScheduler 后台调度器进行孤立账号清理。"""
    global _scheduler

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning(
            "apscheduler 未安装 — 孤立账号清理调度已禁用。"
            "安装命令: pip install apscheduler"
        )
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        cleanup_orphan_accounts,
        trigger=CronTrigger(hour=3),
        args=[engine],
        id="cleanup_orphan_accounts",
        name="Clean up orphan student accounts",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("孤立账号清理调度已启动（每日 03:00 执行）")


def shutdown_cleanup_scheduler() -> None:
    """关闭清理调度器（如正在运行）。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("孤立账号清理调度已关闭")
