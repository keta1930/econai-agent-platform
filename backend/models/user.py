from datetime import datetime

from sqlalchemy import Column, String, DateTime, CheckConstraint

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'student')", name="ck_users_role"),
    )
