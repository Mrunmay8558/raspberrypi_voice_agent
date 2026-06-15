"""Authentication request schemas."""

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class LoginRequest(BaseModel):
    """Dashboard login payload."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    """Dashboard password-change payload."""

    username: str = Field(min_length=1, max_length=64)
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        """Require a number and a special character in the new password."""
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must include at least one number.")
        if not any(not character.isalnum() for character in value):
            raise ValueError("Password must include at least one special character.")
        return value
