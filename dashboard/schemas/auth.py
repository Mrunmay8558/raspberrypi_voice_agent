from pydantic import BaseModel
from pydantic import Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class AuthResponse(BaseModel):
    ok: bool
