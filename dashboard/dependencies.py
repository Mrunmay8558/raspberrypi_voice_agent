from fastapi import Cookie
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status

from dashboard.core.security import AuthStore
from dashboard.core.security import SESSION_COOKIE_NAME


def get_auth_store(request: Request) -> AuthStore:
    return request.app.state.auth_store


def require_session(
    auth_store: AuthStore = Depends(get_auth_store),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> None:
    if auth_store.verify_session(session_token):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )
