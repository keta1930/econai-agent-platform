from typing import Literal

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    class_name: str
    admin_name: str
    student_id: str
    password: str


class RegisterResponse(BaseModel):
    id: int
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: str
    class_id: int | None = None
    class_name: str | None = None


class ClassOption(BaseModel):
    class_id: int
    class_name: str
    admin_name: str


class ClassSelectionResponse(BaseModel):
    requires_class_selection: Literal[True] = True
    classes: list[ClassOption]


class SelectClassRequest(BaseModel):
    username: str
    password: str
    class_id: int
