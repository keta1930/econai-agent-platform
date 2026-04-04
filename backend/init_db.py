import logging

from config import ENV, SECRET_KEY, _DEFAULT_SECRET_KEY
from database import engine, async_session_factory, Base
from seed import run_seed

# Import all models so Base.metadata knows about them
import models  # noqa: F401

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

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    async with async_session_factory() as db:
        await run_seed(db)
