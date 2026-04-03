from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class BackupCreate(BaseModel):
    display_name: str | None = None


class BackupRename(BaseModel):
    display_name: str

    @field_validator("display_name")
    @classmethod
    def display_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("备份名称不能为空")
        return v.strip()


class BackupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    size: int
    created_at: datetime


class BackupListResponse(BaseModel):
    items: list[BackupResponse]


class BackupDownloadResponse(BaseModel):
    download_url: str
    filename: str
