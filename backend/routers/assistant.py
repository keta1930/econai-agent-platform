"""AI Assistant API routes — conversation CRUD, SSE messaging, file upload."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import require_admin, TokenPayload
from database import get_db
from schemas.assistant import (
    AnswerRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    FileUploadResponse,
    SendMessageRequest,
    UpdateConversationRequest,
)
from services.assistant.service import AssistantService
from services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

ALLOWED_UPLOAD_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls
    "text/csv",  # .csv
}
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def _sse_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


# ------------------------------------------------------------------
# Conversation CRUD
# ------------------------------------------------------------------


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    body: CreateConversationRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    service = AssistantService(db)
    conversation = await service.create_conversation(admin.id, body.title)
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        token_count=conversation.token_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    service = AssistantService(db)
    conversations = await service.list_conversations(admin.id)
    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c.id,
                title=c.title,
                status=c.status,
                token_count=c.token_count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ]
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    service = AssistantService(db)
    return await service.get_conversation(conversation_id, admin.id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = AssistantService(db)
    await service.delete_conversation(conversation_id, admin.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation_title(
    conversation_id: uuid.UUID,
    body: UpdateConversationRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    service = AssistantService(db)
    conversation = await service.update_conversation_title(
        conversation_id, admin.id, body.title,
    )
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        token_count=conversation.token_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


# ------------------------------------------------------------------
# Messaging (SSE Streaming)
# ------------------------------------------------------------------


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    service = AssistantService(db)
    files = [f.model_dump() for f in body.files] if body.files else None
    return StreamingResponse(
        service.handle_message(
            conversation_id, admin.id, body.content,
            files=files,
            class_id=body.class_id,
        ),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.post("/conversations/{conversation_id}/answer")
async def answer_question(
    conversation_id: uuid.UUID,
    body: AnswerRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    service = AssistantService(db)
    return StreamingResponse(
        service.handle_answer(conversation_id, admin.id, body.answer),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.post("/conversations/{conversation_id}/stop")
async def stop_generation(
    conversation_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    service = AssistantService(db)
    # Verify the conversation belongs to this admin before allowing cancellation
    await service._load_owned_conversation(conversation_id, admin.id)
    await service.stop_generation(conversation_id)
    return {"status": "ok"}


# ------------------------------------------------------------------
# File Upload
# ------------------------------------------------------------------


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    admin: TokenPayload = Depends(require_admin),
) -> FileUploadResponse:
    # Validate extension
    filename = file.filename or "unknown"
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式，仅支持 {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大 {MAX_UPLOAD_SIZE // 1024 // 1024}MB）",
        )

    # Store to MinIO
    file_id = str(uuid.uuid4())
    object_name = f"assistant/{admin.id}/{file_id}{ext}"
    mime_type = file.content_type or "application/octet-stream"

    await asyncio.to_thread(
        storage_service.put_object, object_name, data, mime_type,
    )

    return FileUploadResponse(
        file_id=object_name,
        filename=filename,
        mime_type=mime_type,
        size=len(data),
    )
