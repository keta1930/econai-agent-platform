import os

SECRET_KEY: str = os.getenv("SECRET_KEY", "hw-grading-secret-key-change-in-production")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data.db")
STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")
TOKEN_EXPIRE_HOURS: int = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))
DEFAULT_ADMIN_ID: str = "xueheng26"
DEFAULT_ADMIN_PASSWORD: str = "vibeai26"
