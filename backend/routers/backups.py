import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import require_admin, TokenPayload
from database import get_db
from schemas.backup import (
    BackupCreate,
    BackupRename,
    BackupResponse,
    BackupListResponse,
)
from services import backup_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/backups", tags=["admin-backups"])


@router.post("", response_model=BackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup(
    body: BackupCreate | None = None,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("创建备份 — 管理员=%s", admin.id)
    try:
        backup = await backup_service.create_backup(
            db, admin.id, body.display_name if body else None,
        )
    except ValueError as e:
        logger.warning("创建备份失败 — %s", e)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return backup


@router.get("", response_model=BackupListResponse)
async def list_backups(
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await backup_service.list_backups(db, admin.id)
    return BackupListResponse(items=items)


@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("下载备份 — backup_id=%s, 管理员=%s", backup_id, admin.id)
    try:
        file_path, filename = await backup_service.get_backup_file_path(
            db, backup_id, admin.id,
        )
    except ValueError as e:
        logger.warning("下载备份失败 — %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/json",
    )


@router.patch("/{backup_id}", response_model=BackupResponse)
async def rename_backup(
    backup_id: uuid.UUID,
    body: BackupRename,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("重命名备份 — backup_id=%s, 新名称=%s", backup_id, body.display_name)
    try:
        backup = await backup_service.rename_backup(
            db, backup_id, admin.id, body.display_name,
        )
    except ValueError as e:
        logger.warning("重命名备份失败 — %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return backup


@router.delete("/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    backup_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("删除备份 — backup_id=%s, 管理员=%s", backup_id, admin.id)
    try:
        await backup_service.delete_backup(db, backup_id, admin.id)
    except ValueError as e:
        logger.warning("删除备份失败 — %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
