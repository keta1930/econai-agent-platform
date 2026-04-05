from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey,
    Index, Integer, String, Uuid, func, text,
)

from database import Base
from utils import uuid7


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid7)
    username = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    password_change_count = Column(Integer, nullable=False, server_default="0")
    invite_code_id = Column(Uuid, ForeignKey("invite_codes.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "role IN ('super_admin', 'admin', 'student')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "password_change_count >= 0 AND password_change_count <= 3",
            name="ck_users_password_change_count",
        ),
        Index(
            "uq_student_username",
            "username",
            unique=True,
            postgresql_where=text("role = 'student'"),
        ),
        Index(
            "uq_admin_username",
            "username",
            unique=True,
            postgresql_where=text("role IN ('admin', 'super_admin')"),
        ),
    )
