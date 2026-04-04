import uuid
from typing import Literal

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    class_name: str
    admin_name: str
    student_id: str
    password: str


class RegisterResponse(BaseModel):
    id: uuid.UUID
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    role: str
    class_id: uuid.UUID | None = None
    class_name: str | None = None


class ClassOption(BaseModel):
    class_id: uuid.UUID
    class_name: str
    admin_name: str


class ClassSelectionResponse(BaseModel):
    requires_class_selection: Literal[True] = True
    classes: list[ClassOption]


class SelectClassRequest(BaseModel):
    username: str
    password: str
    class_id: uuid.UUID


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TeacherRegisterRequest(BaseModel):
    invite_code: str
    username: str
    password: str


class TeacherRegisterResponse(BaseModel):
    id: uuid.UUID
    role: str
