import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.auth import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
    ClassSelectionResponse, ClassOption,
    JoinClassRequiresResponse,
    SelectClassRequest,
    JoinClassRequest, JoinClassResponse,
    SwitchClassRequest,
    CaptchaResponse,
    ChangePasswordRequest, ChangePasswordResponse,
    UpdateProfileRequest, UpdateProfileResponse,
    MyClassesResponse, MyClassItem,
    RefreshRequest, RefreshResponse, LogoutRequest,
    TeacherRegisterRequest, TeacherRegisterResponse,
)
from services.auth_service import (
    register_student, authenticate_user,
    select_class as select_class_service,
    join_class as join_class_service,
    switch_class as switch_class_service,
    change_student_password,
    update_student_profile,
    get_student_classes,
    create_refresh_token_record,
    refresh_access_token, revoke_refresh_token,
    register_teacher,
)
from services.captcha_service import generate_captcha, validate_captcha
from auth.jwt import create_access_token
from auth.deps import get_current_user, require_student, TokenPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
student_router = APIRouter(prefix="/api/student", tags=["student-auth"])


# ---------------------------------------------------------------------------
# 验证码
# ---------------------------------------------------------------------------


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha():
    try:
        captcha_id, question = generate_captcha()
    except ValueError:
        logger.warning("验证码生成失败 — 服务不可用")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="验证码服务暂时不可用，请稍后重试",
        )
    return CaptchaResponse(captcha_id=captcha_id, question=question)


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    logger.info("学生注册 — student_id=%s", req.student_id)
    user = await register_student(db, req.student_id, req.password)
    return RegisterResponse(id=user.id, role=user.role)


@router.post(
    "/register-teacher",
    response_model=TeacherRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_teacher_endpoint(
    req: TeacherRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info("教师注册 — username=%s", req.username)
    user = await register_teacher(db, req.invite_code, req.username, req.password)
    return TeacherRegisterResponse(id=user.id, role=user.role)


# ---------------------------------------------------------------------------
# 登录
# ---------------------------------------------------------------------------


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await authenticate_user(db, req.username, req.password)
    user = result["user"]

    if result["type"] == "no_class":
        # 用户未加入任何班级，签发临时 token（class_id=None）
        access_token = create_access_token(
            sub=user.id, role=user.role, class_id=None,
            display_name=user.display_name,
        )
        refresh_token = await create_refresh_token_record(
            db, user.id, class_id=None
        )
        await db.commit()
        logger.info("登录成功（无班级）— user_id=%s", user.id)
        return JoinClassRequiresResponse(
            temp_access_token=access_token,
            temp_refresh_token=refresh_token,
        )

    if result["type"] == "multi_class":
        # 用户属于多个班级，签发临时 token 供客户端调用 select-class
        temp_access = create_access_token(
            sub=user.id, role=user.role, class_id=None,
            display_name=user.display_name,
        )
        temp_refresh = await create_refresh_token_record(
            db, user.id, class_id=None
        )
        await db.commit()
        logger.info("登录成功（多班级选择）— user_id=%s", user.id)
        return ClassSelectionResponse(
            temp_access_token=temp_access,
            temp_refresh_token=temp_refresh,
            classes=[ClassOption(**c) for c in result["classes"]],
        )

    # 单一用户：admin/super_admin 或只属于一个班级的学生
    class_id = None
    class_name = None
    admin_name = None
    if "class_info" in result:
        info = result["class_info"]
        class_id = info["class_id"]
        class_name = info["class_name"]
        admin_name = info["admin_name"]

    token = create_access_token(
        sub=user.id, role=user.role, class_id=class_id,
        display_name=user.display_name,
    )
    refresh_token = await create_refresh_token_record(
        db, user.id, class_id=class_id
    )
    await db.commit()

    logger.info("登录成功 — user_id=%s, role=%s", user.id, user.role)
    return LoginResponse(
        access_token=token,
        refresh_token=refresh_token,
        role=user.role,
        class_id=class_id,
        class_name=class_name,
        admin_name=admin_name,
    )


# ---------------------------------------------------------------------------
# 班级选择（Bearer 认证，无需密码）
# ---------------------------------------------------------------------------


@router.post("/login/select-class", response_model=LoginResponse)
async def select_class(
    req: SelectClassRequest,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info("选择班级 — user_id=%s, class_id=%s", user.id, req.class_id)
    data = await select_class_service(db, user.id, req.class_id)
    return LoginResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        role=data["role"],
        class_id=data["class_id"],
        class_name=data["class_name"],
        admin_name=data["admin_name"],
    )


# ---------------------------------------------------------------------------
# 加入 / 切换班级（仅学生）
# ---------------------------------------------------------------------------


@student_router.post("/join-class", response_model=JoinClassResponse)
async def join_class(
    req: JoinClassRequest,
    user: TokenPayload = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    logger.info("加入班级 — user_id=%s", user.id)
    data = await join_class_service(db, user.id, req.join_token)
    return JoinClassResponse(
        class_id=data["class_id"],
        class_name=data["class_name"],
        admin_name=data["admin_name"],
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
    )


@student_router.post("/switch-class", response_model=LoginResponse)
async def switch_class(
    req: SwitchClassRequest,
    user: TokenPayload = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    logger.info("切换班级 — user_id=%s, class_id=%s", user.id, req.class_id)
    data = await switch_class_service(db, user.id, req.class_id)
    return LoginResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        role=data["role"],
        class_id=data["class_id"],
        class_name=data["class_name"],
        admin_name=data["admin_name"],
    )


# ---------------------------------------------------------------------------
# 修改密码（仅学生）
# ---------------------------------------------------------------------------


@student_router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    req: ChangePasswordRequest,
    user: TokenPayload = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    logger.info("修改密码 — user_id=%s", user.id)
    count = await change_student_password(db, user.id, req.current_password, req.new_password)
    return ChangePasswordResponse(password_change_count=count)


@student_router.put("/profile", response_model=UpdateProfileResponse)
async def update_profile(
    req: UpdateProfileRequest,
    user: TokenPayload = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    logger.info("更新个人资料 — user_id=%s", user.id)
    display_name = await update_student_profile(db, user.id, req.display_name)
    return UpdateProfileResponse(display_name=display_name)


@student_router.get("/my-classes", response_model=MyClassesResponse)
async def my_classes(
    user: TokenPayload = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    classes = await get_student_classes(db, user.id)
    return MyClassesResponse(
        classes=[MyClassItem(**c) for c in classes]
    )


# ---------------------------------------------------------------------------
# Token 刷新 / 登出
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    access_token = await refresh_access_token(db, req.refresh_token)
    return RefreshResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(req: LogoutRequest, db: AsyncSession = Depends(get_db)):
    logger.info("用户登出")
    await revoke_refresh_token(db, req.refresh_token)
    return Response(status_code=204)
