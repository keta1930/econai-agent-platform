from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from auth.deps import require_admin
from models.model_config import ModelConfig
from schemas.model_config import (
    ModelConfigCreateRequest, ModelConfigResponse,
    ModelConfigListResponse, ModelActivateResponse,
)

router = APIRouter(
    prefix="/api/admin/models",
    tags=["models"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=ModelConfigListResponse)
def list_models(db: Session = Depends(get_db)):
    configs = db.query(ModelConfig).order_by(ModelConfig.created_at.desc()).all()
    return ModelConfigListResponse(
        items=[ModelConfigResponse.model_validate(c) for c in configs]
    )


@router.post("", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED)
def create_model(req: ModelConfigCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(ModelConfig).filter(ModelConfig.name == req.name).first()
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
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return ModelConfigResponse.model_validate(config)


@router.put("/{model_id}/activate", response_model=ModelActivateResponse)
def activate_model(model_id: int, db: Session = Depends(get_db)):
    target = db.query(ModelConfig).filter(ModelConfig.id == model_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )
    # Deactivate all, then activate target
    db.query(ModelConfig).update({ModelConfig.is_active: False})
    target.is_active = True
    db.commit()
    return ModelActivateResponse(message="模型已激活", active_model=target.name)
