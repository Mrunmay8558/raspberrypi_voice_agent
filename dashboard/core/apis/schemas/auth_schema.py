"""Compatibility exports for dashboard authentication schemas."""

from dashboard.core.apis.schemas.requests.auth_request import ChangePasswordRequest
from dashboard.core.apis.schemas.requests.auth_request import LoginRequest
from dashboard.core.apis.schemas.responses.auth_response import AuthResponse

__all__ = ["AuthResponse", "ChangePasswordRequest", "LoginRequest"]
