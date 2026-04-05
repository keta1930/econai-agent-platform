import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


# --- Requests ---

class CreateConversationRequest(BaseModel):
    title: str | None = None


class UpdateConversationRequest(BaseModel):
    title: str


class FileRef(BaseModel):
    """Reference to a previously uploaded file."""
    file_id: str
    filename: str
    mime_type: str


class SendMessageRequest(BaseModel):
    content: str
    class_id: uuid.UUID | None = None
    files: list[FileRef] = []


class AnswerRequest(BaseModel):
    answer: str


# --- Block types for message content ---

BlockType = Literal["text", "tool_use", "tool_result", "file"]


class TextBlock(BaseModel):
    type: Literal["text"]
    text: str


class ToolUseBlock(BaseModel):
    type: Literal["tool_use"]
    tool_call_id: str
    name: str
    input: dict


class ToolResultBlock(BaseModel):
    type: Literal["tool_result"]
    tool_call_id: str
    content: str
    is_error: bool = False


class FileBlock(BaseModel):
    type: Literal["file"]
    file_id: str
    filename: str
    mime_type: str


BlockSchema = TextBlock | ToolUseBlock | ToolResultBlock | FileBlock


# --- Responses ---

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    mime_type: str
    size: int


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: list[BlockSchema]
    token_count: int
    created_at: datetime


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    status: str
    token_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
