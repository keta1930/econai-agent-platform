from datetime import datetime

from pydantic import BaseModel


class UserInfo(BaseModel):
    id: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
