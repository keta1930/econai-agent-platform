from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, Uuid, func

from database import Base
from utils import uuid7


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(Uuid, primary_key=True, default=uuid7)
    conversation_id = Column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    query = Column(String, nullable=False)
    relevance_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
