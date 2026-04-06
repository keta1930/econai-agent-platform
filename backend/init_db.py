import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from config import ENV, SECRET_KEY, _DEFAULT_SECRET_KEY
from database import async_session_factory
from seed import run_seed

# Import all models so Base.metadata knows about them
import models  # noqa: F401

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent


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


def _run_migrations() -> None:
    """Run Alembic migrations (upgrade head) programmatically."""
    alembic_cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    # alembic.ini uses %(here)s which resolves relative to the ini file,
    # but we need to ensure the working directory context is correct.
    alembic_cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    command.upgrade(alembic_cfg, "head")


async def init_database():
    _check_secret_key()

    logger.info("Running Alembic migrations...")
    _run_migrations()
    logger.info("Database migrations complete")

    async with async_session_factory() as db:
        await run_seed(db)
