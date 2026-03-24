import logging

from sqlalchemy import text

from database import engine, SessionLocal, Base
from models import User, ModelConfig
from services.auth_service import hash_password
from config import (
    DEFAULT_ADMIN_ID,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_API_KEY,
    DEFAULT_MODEL_BASE_URL,
    DEFAULT_MODEL_ADAPTER,
)

logger = logging.getLogger(__name__)


def _migrate_tasks_table(db):
    """Add status and updated_at columns to tasks table if missing."""
    rows = db.execute(text("PRAGMA table_info(tasks)")).fetchall()
    existing_columns = {row[1] for row in rows}

    if "status" not in existing_columns:
        db.execute(text(
            "ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'published'"
        ))
        logger.info("Migrated tasks table: added 'status' column")

    if "updated_at" not in existing_columns:
        db.execute(text(
            "ALTER TABLE tasks ADD COLUMN updated_at TIMESTAMP DEFAULT NULL"
        ))
        logger.info("Migrated tasks table: added 'updated_at' column")


def init_database():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _migrate_tasks_table(db)
        # Default admin
        if not db.query(User).filter(User.id == DEFAULT_ADMIN_ID).first():
            admin = User(
                id=DEFAULT_ADMIN_ID,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)

        # Default model config
        if not db.query(ModelConfig).filter(ModelConfig.name == DEFAULT_MODEL_NAME).first():
            model = ModelConfig(
                name=DEFAULT_MODEL_NAME,
                api_key=DEFAULT_MODEL_API_KEY,
                base_url=DEFAULT_MODEL_BASE_URL,
                adapter_type=DEFAULT_MODEL_ADAPTER,
                is_active=True,
            )
            db.add(model)

        db.commit()
    finally:
        db.close()
