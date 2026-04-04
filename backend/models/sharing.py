from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Uuid, func
from sqlalchemy.orm import relationship

from database import Base
from utils import uuid7


class SharingTopic(Base):
    __tablename__ = "sharing_topics"

    id = Column(Uuid, primary_key=True, default=uuid7)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="voting")
    presenters = Column(String, nullable=True)
    session_number = Column(Integer, nullable=True)
    shared_at = Column(DateTime(timezone=True), nullable=True)
    materials_content = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    submitted_by = Column(Uuid, ForeignKey("users.id"), nullable=True)
    class_id = Column(Uuid, ForeignKey("classes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    votes = relationship("TopicVote", back_populates="topic", cascade="all, delete-orphan")
    submitter = relationship("User", foreign_keys=[submitted_by])


class TopicVote(Base):
    __tablename__ = "topic_votes"

    id = Column(Uuid, primary_key=True, default=uuid7)
    topic_id = Column(Uuid, ForeignKey("sharing_topics.id"), nullable=False)
    student_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    topic = relationship("SharingTopic", back_populates="votes")

    __table_args__ = (
        UniqueConstraint("topic_id", "student_id", name="uq_vote_topic_student"),
    )
