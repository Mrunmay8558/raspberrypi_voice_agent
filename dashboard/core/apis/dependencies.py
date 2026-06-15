"""Shared FastAPI dependencies for dashboard APIs.

This module provides reusable request-time dependencies used by dashboard
routes, such as resolving the auth store from application state and enforcing
an authenticated browser session.
"""

from fastapi import Cookie
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status

from dashboard.commons.auth import AuthStore
from dashboard.commons.auth import SESSION_COOKIE_NAME


def get_auth_store(request: Request) -> AuthStore:
    """Return the dashboard auth store from application state.

    Args:
        request: Incoming FastAPI request.

    Returns:
        AuthStore: App-scoped dashboard authentication store.
    """
    return request.app.state.auth_store


def require_session(
    auth_store: AuthStore = Depends(get_auth_store),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> None:
    """Reject requests that do not carry a valid dashboard session.

    Args:
        auth_store: Auth store resolved from FastAPI dependency injection.
        session_token: Dashboard session cookie value.

    Raises:
        HTTPException: Raised with 401 when the session is missing or invalid.
    """
    if auth_store.verify_session(session_token):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )
