import uuid
from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Student registration
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    student_id: str
    college: Literal["lingnan", "physics"]
    password: str


class RegisterResponse(BaseModel):
    id: uuid.UUID
    role: str


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    role: str
    class_id: uuid.UUID | None = None
    class_name: str | None = None
    admin_name: str | None = None


class ClassOption(BaseModel):
    class_id: uuid.UUID
    class_name: str
    admin_name: str


class ClassSelectionResponse(BaseModel):
    requires_class_selection: Literal[True] = True
    temp_access_token: str
    temp_refresh_token: str
    classes: list[ClassOption]


class JoinClassRequiresResponse(BaseModel):
    requires_join_class: Literal[True] = True
    temp_access_token: str
    temp_refresh_token: str


# ---------------------------------------------------------------------------
# Class selection / switching / joining
# ---------------------------------------------------------------------------


class SelectClassRequest(BaseModel):
    class_id: uuid.UUID


class SwitchClassRequest(BaseModel):
    class_id: uuid.UUID


class JoinClassRequest(BaseModel):
    join_token: str


class JoinClassResponse(BaseModel):
    class_id: uuid.UUID
    class_name: str
    admin_name: str
    access_token: str
    refresh_token: str


# ---------------------------------------------------------------------------
# CAPTCHA
# ---------------------------------------------------------------------------


class CaptchaResponse(BaseModel):
    captcha_id: str
    question: str


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class UpdateProfileRequest(BaseModel):
    display_name: str


class UpdateProfileResponse(BaseModel):
    display_name: str


# ---------------------------------------------------------------------------
# Student classes
# ---------------------------------------------------------------------------


class MyClassItem(BaseModel):
    class_id: uuid.UUID
    class_name: str
    admin_name: str


class MyClassesResponse(BaseModel):
    classes: list[MyClassItem]


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    password_change_count: int


# ---------------------------------------------------------------------------
# Token refresh / logout
# ---------------------------------------------------------------------------


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Teacher registration (unchanged)
# ---------------------------------------------------------------------------


class TeacherRegisterRequest(BaseModel):
    invite_code: str
    username: str
    password: str


class TeacherRegisterResponse(BaseModel):
    id: uuid.UUID
    role: str
