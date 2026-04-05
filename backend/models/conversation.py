from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from database import Base
from utils import uuid7


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Uuid, primary_key=True, default=uuid7)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    class_id = Column(Uuid, ForeignKey("classes.id"), nullable=True)
    title = Column(String(200), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    pending_tool_call_id = Column(String(100), nullable=True)
    token_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Uuid, primary_key=True, default=uuid7)
    conversation_id = Column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(JSONB, nullable=False)
    token_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
