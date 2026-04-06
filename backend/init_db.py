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


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    return cfg


# Revision that matches the schema created by the old Base.metadata.create_all.
# Used once to stamp existing databases, then never triggered again.
_CREATE_ALL_REVISION = "6bafd916a45d"


def _stamp_existing_database() -> None:
    """One-time transition: if DB was built by create_all, stamp alembic_version."""
    from sqlalchemy import create_engine, inspect
    from config import DATABASE_URL

    sync_url = DATABASE_URL.replace("+asyncpg", "+psycopg")
    engine = create_engine(sync_url)
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if "users" in tables and "alembic_version" not in tables:
            command.stamp(_alembic_config(), _CREATE_ALL_REVISION)
            logger.info(
                "Auto-stamped existing database to %s", _CREATE_ALL_REVISION,
            )
    finally:
        engine.dispose()


def _run_migrations() -> None:
    """Run Alembic migrations (upgrade head) programmatically."""
    _stamp_existing_database()
    command.upgrade(_alembic_config(), "head")


async def init_database():
    _check_secret_key()

    logger.info("Running Alembic migrations...")
    _run_migrations()
    logger.info("Database migrations complete")

    async with async_session_factory() as db:
        await run_seed(db)
