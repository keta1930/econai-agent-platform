import re

from fastapi import APIRouter, Depends, HTTPException, status

from auth.deps import require_admin
from models.user import User
from schemas.backup import BackupInfo, BackupListResponse, BackupDownloadResponse
from services import backup_service

router = APIRouter(prefix="/api/admin/backups", tags=["admin-backups"])

_BACKUP_FILENAME_RE = re.compile(r"^backup_\d{8}_\d{6}\.sql$")


def _validate_backup_filename(filename: str) -> None:
    if not _BACKUP_FILENAME_RE.match(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的备份文件名",
        )


@router.get("", response_model=BackupListResponse)
async def list_backups(_admin: User = Depends(require_admin)):
    items = await backup_service.list_backups()
    return BackupListResponse(items=items)


@router.post("", response_model=BackupInfo)
async def create_backup(_admin: User = Depends(require_admin)):
    try:
        return await backup_service.create_backup()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e),
        )


@router.get("/{filename}", response_model=BackupDownloadResponse)
async def download_backup(
    filename: str, _admin: User = Depends(require_admin),
):
    _validate_backup_filename(filename)
    try:
        url = await backup_service.get_backup_download_url(filename)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="备份文件不存在",
        )
    return BackupDownloadResponse(download_url=url)


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    filename: str, _admin: User = Depends(require_admin),
):
    _validate_backup_filename(filename)
    try:
        await backup_service.delete_backup(filename)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="备份文件不存在",
        )
