from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import require_admin
from database import get_db
from models.user import User
from schemas.backup import (
    BackupCreate,
    BackupRename,
    BackupResponse,
    BackupListResponse,
    BackupDownloadResponse,
)
from services import backup_service

router = APIRouter(prefix="/api/admin/backups", tags=["admin-backups"])


@router.post("", response_model=BackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup(
    body: BackupCreate | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        backup = await backup_service.create_backup(
            db, admin, body.display_name if body else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return backup


@router.get("", response_model=BackupListResponse)
async def list_backups(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await backup_service.list_backups(db, admin.id)
    return BackupListResponse(items=items)


@router.get("/{backup_id}/download", response_model=BackupDownloadResponse)
async def download_backup(
    backup_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        url, filename = await backup_service.get_backup_download_url(
            db, backup_id, admin.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return BackupDownloadResponse(download_url=url, filename=filename)


@router.patch("/{backup_id}", response_model=BackupResponse)
async def rename_backup(
    backup_id: int,
    body: BackupRename,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        backup = await backup_service.rename_backup(
            db, backup_id, admin.id, body.display_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return backup


@router.delete("/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    backup_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await backup_service.delete_backup(db, backup_id, admin.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
