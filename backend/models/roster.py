from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Uuid, func

from database import Base
from utils import uuid7


class StudentRoster(Base):
    __tablename__ = "student_roster"

    id = Column(Uuid, primary_key=True, default=uuid7)
    student_id = Column(String, nullable=False)
    class_id = Column(Uuid, ForeignKey("classes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("student_id", "class_id", name="uq_roster_student_class"),
    )
