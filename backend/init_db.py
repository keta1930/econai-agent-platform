import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from config import ENV, SECRET_KEY, _DEFAULT_SECRET_KEY
from database import async_session_factory
from seed import run_seed

_ALEMBIC_INI = str(Path(__file__).resolve().parent / "alembic.ini")

logger = logging.getLogger(__name__)


def _check_secret_key() -> None:
    if SECRET_KEY != _DEFAULT_SECRET_KEY:
        return

    if ENV == "production":
        raise RuntimeError(
            "SECRET_KEY must be set in production. "
            "Set the SECRET_KEY environment variable."
        )

    logger.warning(
        "SECURITY WARNING: Using default SECRET_KEY. "
        "Set SECRET_KEY environment variable for production use."
    )


async def init_database():
    _check_secret_key()

    cfg = Config(_ALEMBIC_INI)
    await asyncio.to_thread(command.upgrade, cfg, "head")

    async with async_session_factory() as db:
        await run_seed(db)
