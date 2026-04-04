import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_admin, TokenPayload
from models.model_config import ModelConfig
from schemas.model_config import (
    ModelConfigCreateRequest, ModelConfigResponse,
    ModelConfigListResponse, ModelActivateResponse,
)

router = APIRouter(
    prefix="/api/admin/models",
    tags=["models"],
)


@router.get("", response_model=ModelConfigListResponse)
async def list_models(
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ModelConfig)
        .where(ModelConfig.admin_id == admin.id)
        .order_by(ModelConfig.created_at.desc())
    )
    configs = result.scalars().all()
    return ModelConfigListResponse(
        items=[ModelConfigResponse.model_validate(c) for c in configs]
    )


@router.post("", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    req: ModelConfigCreateRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ModelConfig).where(
            ModelConfig.name == req.name, ModelConfig.admin_id == admin.id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="模型名称已存在",
        )
    config = ModelConfig(
        name=req.name,
        api_key=req.api_key,
        base_url=req.base_url,
        adapter_type=req.adapter_type,
        admin_id=admin.id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return ModelConfigResponse.model_validate(config)


@router.put("/{model_id}/activate", response_model=ModelActivateResponse)
async def activate_model(
    model_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )
    if target.admin_id != admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作",
        )

    # Deactivate all models for this admin, then activate target
    await db.execute(
        update(ModelConfig)
        .where(ModelConfig.admin_id == admin.id)
        .values(is_active=False)
    )
    target.is_active = True
    await db.commit()
    return ModelActivateResponse(message="模型已激活", active_model=target.name)
