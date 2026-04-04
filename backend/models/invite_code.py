from sqlalchemy import Column, String, DateTime, Uuid, func

from database import Base
from utils import uuid7


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Uuid, primary_key=True, default=uuid7)
    category = Column(String, nullable=False)
    code_hash = Column(String, nullable=False, unique=True)
    code_prefix = Column(String(8), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
