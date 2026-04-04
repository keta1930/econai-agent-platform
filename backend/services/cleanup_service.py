"""Orphan account cleanup service.

Periodically removes student accounts that have no class memberships
and were created more than 15 days ago. Associated refresh_tokens are
cleaned up via CASCADE on the FK constraint.
"""

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

_scheduler = None

ORPHAN_RETENTION_DAYS = 15


async def cleanup_orphan_accounts(engine: AsyncEngine) -> int:
    """Delete student accounts with no class memberships older than ORPHAN_RETENTION_DAYS.

    Returns the number of deleted accounts.
    """
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=ORPHAN_RETENTION_DAYS)

        # Use raw SQL for a single efficient DELETE with subquery
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
        logger.info("Cleanup: removed %d orphan student account(s)", deleted)
    return deleted


def start_cleanup_scheduler(engine: AsyncEngine) -> None:
    """Start the APScheduler background scheduler for orphan cleanup."""
    global _scheduler

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning(
            "apscheduler not installed — orphan cleanup scheduler disabled. "
            "Install with: pip install apscheduler"
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
    logger.info("Orphan cleanup scheduler started (runs daily at 03:00)")


def shutdown_cleanup_scheduler() -> None:
    """Shut down the cleanup scheduler if running."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Orphan cleanup scheduler shut down")
