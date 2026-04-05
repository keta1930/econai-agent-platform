from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, CheckConstraint, func

from database import Base
from utils import uuid7


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"

    id = Column(Uuid, primary_key=True, default=uuid7)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Uuid, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, server_default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved')", name="ck_reset_request_status"),
    )
