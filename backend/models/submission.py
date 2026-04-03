from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint, func,
)
from sqlalchemy.orm import relationship

from database import Base


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    file_path = Column(String, nullable=False)
    content_type = Column(String, nullable=False, default="file", server_default="file")
    status = Column(String, nullable=False, default="pending")
    score = Column(Float, nullable=True)
    suggestion = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    graded_at = Column(DateTime(timezone=True), nullable=True)

    task = relationship("Task", back_populates="submissions")

    __table_args__ = (
        UniqueConstraint(
            "task_id", "student_id", "version",
            name="uq_submission_task_student_version",
        ),
        CheckConstraint(
            "status IN ('pending', 'grading', 'completed', 'failed', 'manual_review')",
            name="ck_submissions_status",
        ),
        CheckConstraint(
            "content_type IN ('text', 'file', 'image')",
            name="ck_submissions_content_type",
        ),
    )
