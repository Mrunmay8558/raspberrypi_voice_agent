from fastapi import APIRouter
from fastapi import Cookie
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi import status

from dashboard.core.security import SESSION_COOKIE_NAME
from dashboard.dependencies import get_auth_store
from dashboard.dependencies import require_session
from dashboard.schemas.auth import AuthResponse
from dashboard.schemas.auth import ChangePasswordRequest
from dashboard.schemas.auth import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, auth_store=Depends(get_auth_store)):
    if not auth_store.verify_password(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = auth_store.create_session(payload.username)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="strict",
        max_age=60 * 60 * 12,
    )
    return AuthResponse(ok=True)


@router.post("/logout", response_model=AuthResponse)
def logout(
    response: Response,
    auth_store=Depends(get_auth_store),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    auth_store.revoke_session(session_token)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return AuthResponse(ok=True)


@router.post(
    "/password",
    response_model=AuthResponse,
    dependencies=[Depends(require_session)],
)
def change_password(
    payload: ChangePasswordRequest,
    auth_store=Depends(get_auth_store),
):
    if not auth_store.change_password(
        payload.username, payload.current_password, payload.new_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    return AuthResponse(ok=True)
