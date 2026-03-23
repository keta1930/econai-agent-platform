from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, CheckConstraint

from database import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    api_key = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    adapter_type = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "adapter_type IN ('openai', 'anthropic')",
            name="ck_model_configs_adapter_type",
        ),
    )
