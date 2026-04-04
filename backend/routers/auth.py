from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.class_ import Class
from schemas.auth import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
    ClassSelectionResponse, ClassOption,
    SelectClassRequest,
    RefreshRequest, RefreshResponse, LogoutRequest,
    TeacherRegisterRequest, TeacherRegisterResponse,
)
from services.auth_service import (
    register_student, authenticate_user, authenticate_user_with_class,
    create_refresh_token_record,
    refresh_access_token, revoke_refresh_token,
    register_teacher,
)
from auth.jwt import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await register_student(
        db, req.class_name, req.admin_name, req.student_id, req.password
    )
    return RegisterResponse(id=user.id, role=user.role)


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await authenticate_user(db, req.username, req.password)

    if isinstance(result, list):
        return ClassSelectionResponse(
            classes=[ClassOption(**opt) for opt in result],
        )

    user: User = result
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    class_name: str | None = None
    if user.class_id:
        cls_result = await db.execute(
            select(Class).where(Class.id == user.class_id)
        )
        cls = cls_result.scalar_one_or_none()
        class_name = cls.name if cls else None

    token = create_access_token(
        sub=user.id, role=user.role, class_id=user.class_id
    )
    refresh_token = await create_refresh_token_record(db, user.id)
    await db.commit()

    return LoginResponse(
        access_token=token,
        refresh_token=refresh_token,
        role=user.role,
        class_id=user.class_id,
        class_name=class_name,
    )


@router.post("/login/select-class", response_model=LoginResponse)
async def select_class(req: SelectClassRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user_with_class(
        db, req.username, req.password, req.class_id
    )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    class_name: str | None = None
    if user.class_id:
        cls_result = await db.execute(
            select(Class).where(Class.id == user.class_id)
        )
        cls = cls_result.scalar_one_or_none()
        class_name = cls.name if cls else None

    token = create_access_token(
        sub=user.id, role=user.role, class_id=user.class_id
    )
    refresh_token = await create_refresh_token_record(db, user.id)
    await db.commit()

    return LoginResponse(
        access_token=token,
        refresh_token=refresh_token,
        role=user.role,
        class_id=user.class_id,
        class_name=class_name,
    )


@router.post(
    "/register-teacher",
    response_model=TeacherRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_teacher_endpoint(
    req: TeacherRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await register_teacher(db, req.invite_code, req.username, req.password)
    return TeacherRegisterResponse(id=user.id, role=user.role)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    access_token = await refresh_access_token(db, req.refresh_token)
    return RefreshResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(req: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await revoke_refresh_token(db, req.refresh_token)
    return Response(status_code=204)
