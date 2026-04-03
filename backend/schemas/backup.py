from datetime import datetime

from pydantic import BaseModel


class BackupInfo(BaseModel):
    filename: str
    size: int
    created_at: datetime


class BackupListResponse(BaseModel):
    items: list[BackupInfo]


class BackupDownloadResponse(BaseModel):
    download_url: str
