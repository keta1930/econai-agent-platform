from datetime import datetime

from sqlalchemy import Column, String, DateTime

from database import Base


class StudentRoster(Base):
    __tablename__ = "student_roster"

    student_id = Column(String, primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
