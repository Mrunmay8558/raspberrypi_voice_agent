"""Authentication request schemas."""

from pydantic import BaseModel
from pydantic import Field


class LoginRequest(BaseModel):
    """Dashboard login payload."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    """Dashboard password-change payload."""

    username: str = Field(min_length=1, max_length=64)
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)
