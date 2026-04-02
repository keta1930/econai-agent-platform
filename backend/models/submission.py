from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    student_id = Column(String, ForeignKey("users.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    file_path = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    score = Column(Float, nullable=True)
    suggestion = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    graded_at = Column(DateTime, nullable=True)

    task = relationship("Task", back_populates="submissions")

    __table_args__ = (
        UniqueConstraint(
            "task_id", "student_id", "version",
            name="uq_submission_task_student_version",
        ),
        CheckConstraint(
            "status IN ('pending', 'grading', 'completed', 'failed')",
            name="ck_submissions_status",
        ),
    )
