from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Uuid, func

from database import Base
from utils import uuid7


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Uuid, primary_key=True, default=uuid7)
    name = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    adapter_type = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    admin_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("name", "admin_id", name="uq_model_name_admin"),
        CheckConstraint(
            "adapter_type IN ('openai', 'anthropic')",
            name="ck_model_configs_adapter_type",
        ),
    )
