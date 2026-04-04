import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ModelConfigCreateRequest(BaseModel):
    name: str
    api_key: str
    base_url: str
    adapter_type: Literal["openai", "anthropic"]


class ModelConfigResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_url: str
    adapter_type: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelConfigListResponse(BaseModel):
    items: list[ModelConfigResponse]


class ModelActivateResponse(BaseModel):
    message: str
    active_model: str
