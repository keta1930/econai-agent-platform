from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship

from database import Base


class SharingTopic(Base):
    __tablename__ = "sharing_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="voting")
    presenters = Column(String, nullable=True)
    session_number = Column(Integer, nullable=True)
    shared_at = Column(DateTime(timezone=True), nullable=True)
    materials_content = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    votes = relationship("TopicVote", back_populates="topic", cascade="all, delete-orphan")
    submitter = relationship("User", foreign_keys=[submitted_by])


class TopicVote(Base):
    __tablename__ = "topic_votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("sharing_topics.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    topic = relationship("SharingTopic", back_populates="votes")

    __table_args__ = (
        UniqueConstraint("topic_id", "student_id", name="uq_vote_topic_student"),
    )
