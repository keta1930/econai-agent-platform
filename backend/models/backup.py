from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Uuid, func

from database import Base
from utils import uuid7


class Backup(Base):
    __tablename__ = "backups"

    id = Column(Uuid, primary_key=True, default=uuid7)
    admin_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    display_name = Column(String, nullable=False)
    object_key = Column(String, nullable=False, unique=True)
    size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
