import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
load_dotenv(Path(__file__).parent.parent / ".env")

PORT: int = int(os.getenv("PORT", "8000"))
SECRET_KEY: str = os.getenv("SECRET_KEY", "hw-grading-secret-key-change-in-production")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data.db")
STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")
TOKEN_EXPIRE_HOURS: int = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))

DEFAULT_ADMIN_ID: str = os.getenv("DEFAULT_ADMIN_ID", "admin")
DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "changeme")

DEFAULT_MODEL_NAME: str = os.getenv("DEFAULT_MODEL_NAME", "deepseek-chat")
DEFAULT_MODEL_API_KEY: str = os.getenv("DEFAULT_MODEL_API_KEY", "")
DEFAULT_MODEL_BASE_URL: str = os.getenv("DEFAULT_MODEL_BASE_URL", "https://api.deepseek.com/v1")
DEFAULT_MODEL_ADAPTER: str = os.getenv("DEFAULT_MODEL_ADAPTER", "openai")

TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
