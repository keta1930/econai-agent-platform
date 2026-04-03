from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, func

from database import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    adapter_type = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("name", "admin_id", name="uq_model_name_admin"),
        CheckConstraint(
            "adapter_type IN ('openai', 'anthropic')",
            name="ck_model_configs_adapter_type",
        ),
    )
