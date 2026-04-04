from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import relationship

from database import Base
from utils import uuid7


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Uuid, primary_key=True, default=uuid7)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    grading_criteria = Column(Text, nullable=False, default="")
    status = Column(String, nullable=False, default="draft")
    class_id = Column(Uuid, ForeignKey("classes.id"), nullable=False)
    created_by = Column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    submissions = relationship("Submission", back_populates="task")
