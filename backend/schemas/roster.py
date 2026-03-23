from pydantic import BaseModel


class RosterAddRequest(BaseModel):
    student_id: str


class RosterBatchRequest(BaseModel):
    student_ids: list[str]


class RosterItem(BaseModel):
    student_id: str
    registered: bool


class RosterListResponse(BaseModel):
    items: list[RosterItem]
    total: int


class RosterBatchResponse(BaseModel):
    added: int
    duplicates: int
