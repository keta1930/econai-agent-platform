from pydantic import BaseModel


class RegisterRequest(BaseModel):
    student_id: str
    password: str


class RegisterResponse(BaseModel):
    id: str
    role: str


class LoginRequest(BaseModel):
    id: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
