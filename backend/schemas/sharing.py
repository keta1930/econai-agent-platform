import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TopicStatusType = Literal["voting", "confirmed", "completed"]

MAX_VOTES_PER_STUDENT = 3


# --- Requests ---

class TopicCreateRequest(BaseModel):
    title: str
    class_id: uuid.UUID
    status: TopicStatusType = "voting"
    presenters: str | None = None
    session_number: int | None = None
    shared_at: datetime | None = None
    materials_content: str | None = None


class TopicUpdateRequest(BaseModel):
    title: str | None = None
    status: TopicStatusType | None = None
    presenters: str | None = None
    session_number: int | None = None
    shared_at: datetime | None = None
    materials_content: str | None = None


class TopicSuggestRequest(BaseModel):
    title: str


# --- Responses ---

class TopicListItem(BaseModel):
    id: uuid.UUID
    title: str
    status: TopicStatusType
    presenters: str | None
    session_number: int | None
    shared_at: datetime | None
    has_materials: bool
    vote_count: int
    current_user_voted: bool
    is_student_submitted: bool
    submitted_by_name: str | None


class TopicListResponse(BaseModel):
    items: list[TopicListItem]
    total_votes: int


class TopicMaterialsResponse(BaseModel):
    topic_id: uuid.UUID
    title: str
    materials_content: str


class VoteResponse(BaseModel):
    vote_count: int


# --- Admin responses ---

class AdminTopicListItem(TopicListItem):
    materials_content: str | None


class AdminTopicListResponse(BaseModel):
    items: list[AdminTopicListItem]
