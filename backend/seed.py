import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from services.auth_service import hash_password
from config import DEFAULT_ADMIN_ID, DEFAULT_ADMIN_PASSWORD

logger = logging.getLogger(__name__)


async def _seed_super_admin(db: AsyncSession) -> None:
    result = await db.execute(
        select(User).where(User.username == DEFAULT_ADMIN_ID, User.role == "super_admin")
    )
    if result.scalar_one_or_none() is not None:
        return
    pw_hash = await asyncio.to_thread(hash_password, DEFAULT_ADMIN_PASSWORD)
    db.add(User(
        username=DEFAULT_ADMIN_ID,
        password_hash=pw_hash,
        role="super_admin",
    ))


async def run_seed(db: AsyncSession) -> None:
    """Execute all seed data upserts idempotently."""
    await _seed_super_admin(db)
    await db.commit()
    logger.info("Seed data applied")
