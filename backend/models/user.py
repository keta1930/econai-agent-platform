from sqlalchemy import Boolean, Column, String, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Uuid, func

from database import Base
from utils import uuid7


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid7)
    username = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    class_id = Column(Uuid, ForeignKey("classes.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "role IN ('super_admin', 'admin', 'student')",
            name="ck_users_role",
        ),
        UniqueConstraint("username", "class_id", name="uq_user_username_class"),
    )
