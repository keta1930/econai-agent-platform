import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
load_dotenv(Path(__file__).parent.parent / ".env")

PORT: int = int(os.getenv("PORT", "25002"))
ENV: str = os.getenv("ENV", "development")
_DEFAULT_SECRET_KEY = "hw-grading-secret-key-change-in-production"
SECRET_KEY: str = os.getenv("SECRET_KEY", _DEFAULT_SECRET_KEY)
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "3"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# PostgreSQL
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "25001"))
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "homework")

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}",
)

# MinIO
MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:25003")
MINIO_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "homework")
MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

DEFAULT_ADMIN_ID: str = os.getenv("DEFAULT_ADMIN_ID", "admin")
DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "changeme")

TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# Backup
BACKUP_DIR: str = os.getenv("BACKUP_DIR", str(Path(__file__).parent / "backups"))
MAX_BACKUPS_PER_ADMIN: int = int(os.getenv("MAX_BACKUPS_PER_ADMIN", "10"))

# Upload limits (bytes)
MAX_TEXT_SIZE: int = int(os.getenv("MAX_TEXT_SIZE", "2097152"))  # 2 MB
MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", "5242880"))  # 5 MB per image
MAX_IMAGES_PER_SUBMISSION: int = int(os.getenv("MAX_IMAGES_PER_SUBMISSION", "10"))
MAX_IMAGE_TOTAL_SIZE: int = int(os.getenv("MAX_IMAGE_TOTAL_SIZE", "52428800"))  # 50 MB total
