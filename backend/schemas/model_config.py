import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ModelConfigCreateRequest(BaseModel):
    name: str
    api_key: str
    base_url: str
    adapter_type: Literal["openai", "anthropic"]
    supports_vision: bool = False


class ModelConfigUpdateRequest(BaseModel):
    name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    adapter_type: Literal["openai", "anthropic"] | None = None
    supports_vision: bool | None = None


class ModelDeriveRequest(BaseModel):
    source_model_id: uuid.UUID
    name: str
    supports_vision: bool = False


class ModelConfigResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_url: str
    adapter_type: str
    supports_vision: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelConfigListResponse(BaseModel):
    items: list[ModelConfigResponse]


class ModelActivateResponse(BaseModel):
    message: str
    active_model: str
