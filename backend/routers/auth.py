from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.auth import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
)
from services.auth_service import register_student, authenticate_user
from auth.jwt import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    user = register_student(db, req.student_id, req.password)
    return RegisterResponse(id=user.id, role=user.role)


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, req.id, req.password)
    token = create_access_token(sub=user.id, role=user.role)
    return LoginResponse(access_token=token, role=user.role)
