import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_admin, TokenPayload
from models.model_config import ModelConfig
from schemas.model_config import (
    ModelConfigCreateRequest, ModelConfigUpdateRequest,
    ModelDeriveRequest, ModelConfigResponse,
    ModelConfigListResponse, ModelActivateResponse,
)

logger = logging.getLogger(__name__)

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
    logger.info("创建模型配置 — 管理员=%s, 名称=%s", admin.id, req.name)

    result = await db.execute(
        select(ModelConfig).where(
            ModelConfig.name == req.name, ModelConfig.admin_id == admin.id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.warning("创建模型配置失败 — 名称重复, 名称=%s", req.name)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="模型名称已存在",
        )
    config = ModelConfig(
        name=req.name,
        api_key=req.api_key,
        base_url=req.base_url,
        adapter_type=req.adapter_type,
        supports_vision=req.supports_vision,
        admin_id=admin.id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return ModelConfigResponse.model_validate(config)


@router.post("/derive", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED)
async def derive_model(
    req: ModelDeriveRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """从现有模型派生：复用 base_url、api_key、adapter_type，只需指定新名称和视觉支持。"""
    logger.info("派生模型 — 源模型=%s, 新名称=%s, 管理员=%s", req.source_model_id, req.name, admin.id)

    result = await db.execute(select(ModelConfig).where(ModelConfig.id == req.source_model_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="源模型不存在")
    if source.admin_id != admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作")

    # 名称唯一性
    dup = await db.execute(
        select(ModelConfig).where(
            ModelConfig.name == req.name, ModelConfig.admin_id == admin.id
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型名称已存在")

    config = ModelConfig(
        name=req.name,
        api_key=source.api_key,
        base_url=source.base_url,
        adapter_type=source.adapter_type,
        supports_vision=req.supports_vision,
        admin_id=admin.id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return ModelConfigResponse.model_validate(config)


@router.patch("/{model_id}", response_model=ModelConfigResponse)
async def update_model(
    model_id: uuid.UUID,
    req: ModelConfigUpdateRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("更新模型配置 — model_id=%s, 管理员=%s", model_id, admin.id)

    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    if target.admin_id != admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作")

    # 如果改名，检查唯一性
    if req.name is not None and req.name != target.name:
        dup = await db.execute(
            select(ModelConfig).where(
                ModelConfig.name == req.name,
                ModelConfig.admin_id == admin.id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="模型名称已存在",
            )

    # 只更新非 None 字段
    for field in ("name", "api_key", "base_url", "adapter_type", "supports_vision"):
        value = getattr(req, field)
        if value is not None:
            setattr(target, field, value)

    await db.commit()
    await db.refresh(target)
    return ModelConfigResponse.model_validate(target)


@router.put("/{model_id}/activate", response_model=ModelActivateResponse)
async def activate_model(
    model_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("激活模型 — model_id=%s, 管理员=%s", model_id, admin.id)

    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    target = result.scalar_one_or_none()
    if not target:
        logger.warning("激活模型失败 — 模型不存在, model_id=%s", model_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )
    if target.admin_id != admin.id:
        logger.warning("激活模型失败 — 无权操作, model_id=%s, 管理员=%s", model_id, admin.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作",
        )

    # 先停用该管理员的所有模型，再激活目标模型
    await db.execute(
        update(ModelConfig)
        .where(ModelConfig.admin_id == admin.id)
        .values(is_active=False)
    )
    target.is_active = True
    await db.commit()
    return ModelActivateResponse(message="模型已激活", active_model=target.name)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("删除模型配置 — model_id=%s, 管理员=%s", model_id, admin.id)

    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    target = result.scalar_one_or_none()
    if not target:
        logger.warning("删除模型配置失败 — 模型不存在, model_id=%s", model_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )
    if target.admin_id != admin.id:
        logger.warning("删除模型配置失败 — 无权操作, model_id=%s, 管理员=%s", model_id, admin.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作",
        )
    if target.is_active:
        logger.warning("删除模型配置失败 — 不能删除活跃模型, model_id=%s", model_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法删除活跃模型，请先激活其他模型",
        )
    await db.delete(target)
    await db.commit()
