import secrets

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Uuid, func

from database import Base
from utils import uuid7


class Class(Base):
    __tablename__ = "classes"

    id = Column(Uuid, primary_key=True, default=uuid7)
    name = Column(String, nullable=False)
    created_by = Column(Uuid, ForeignKey("users.id"), nullable=False)
    join_token = Column(String, nullable=False, unique=True, default=lambda: secrets.token_urlsafe(16))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("name", "created_by", name="uq_class_name_admin"),
    )
