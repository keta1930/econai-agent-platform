import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from config import ENV, SECRET_KEY, _DEFAULT_SECRET_KEY
from database import async_session_factory
from seed import run_seed

# 导入所有模型，确保 Base.metadata 包含它们
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
        "安全警告: 正在使用默认 SECRET_KEY。"
        "生产环境请设置 SECRET_KEY 环境变量。"
    )


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    return cfg


# 对应旧版 Base.metadata.create_all 创建的 schema 的 revision。
# 仅用于一次性 stamp 已有数据库，之后不再触发。
_CREATE_ALL_REVISION = "6bafd916a45d"


def _stamp_existing_database() -> None:
    """一次性过渡：若数据库由 create_all 创建，则 stamp alembic_version。"""
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
                "已自动 stamp 现有数据库到 %s", _CREATE_ALL_REVISION,
            )
    finally:
        engine.dispose()


def _run_migrations() -> None:
    """以编程方式执行 Alembic 迁移（upgrade head）。"""
    _stamp_existing_database()
    command.upgrade(_alembic_config(), "head")


async def init_database():
    _check_secret_key()

    logger.info("数据库迁移执行中...")
    _run_migrations()
    logger.info("数据库迁移完成")

    async with async_session_factory() as db:
        await run_seed(db)
