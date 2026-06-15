"""Authentication response schemas."""

from pydantic import BaseModel


class AuthResponse(BaseModel):
    """Generic authentication operation result."""

    ok: bool
