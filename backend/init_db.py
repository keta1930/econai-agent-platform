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


def _migrate_submissions_table(db):
    """Add version column and replace unique constraint on submissions table.

    SQLite does not support DROP CONSTRAINT, so we rebuild the table when
    migrating from the old schema (which has the two-column unique constraint
    ``uq_submission_task_student``).
    """
    rows = db.execute(text("PRAGMA table_info(submissions)")).fetchall()
    existing_columns = {row[1] for row in rows}

    if "version" in existing_columns:
        return  # already migrated

    # Rebuild the table: add version column + replace unique constraint
    db.execute(text("""
        CREATE TABLE submissions_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id     INTEGER NOT NULL REFERENCES tasks(id),
            student_id  TEXT    NOT NULL REFERENCES users(id),
            version     INTEGER NOT NULL DEFAULT 1,
            file_path   TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'pending',
            score       REAL,
            suggestion  TEXT,
            submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            graded_at   TIMESTAMP,
            UNIQUE (task_id, student_id, version),
            CHECK (status IN ('pending', 'grading', 'completed', 'failed'))
        )
    """))
    db.execute(text("""
        INSERT INTO submissions_new
            (id, task_id, student_id, version, file_path, status,
             score, suggestion, submitted_at, graded_at)
        SELECT id, task_id, student_id, 1, file_path, status,
               score, suggestion, submitted_at, graded_at
        FROM submissions
    """))
    db.execute(text("DROP TABLE submissions"))
    db.execute(text("ALTER TABLE submissions_new RENAME TO submissions"))
    logger.info("Migrated submissions table: added 'version' column, replaced unique constraint")


def init_database():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _migrate_tasks_table(db)
        _migrate_submissions_table(db)
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
