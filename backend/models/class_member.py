from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, Uuid, func

from database import Base
from utils import uuid7


class ClassMember(Base):
    __tablename__ = "class_members"

    id = Column(Uuid, primary_key=True, default=uuid7)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Uuid, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "class_id", name="uq_class_member"),
    )
