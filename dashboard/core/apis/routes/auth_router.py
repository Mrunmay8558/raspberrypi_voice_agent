"""Authentication routes for the dashboard API."""

from fastapi import APIRouter
from fastapi import Cookie
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status

from config import DASHBOARD_SESSION_TTL_HOURS
from dashboard.core import logger
from dashboard.core.apis.schemas.requests.auth_request import ChangePasswordRequest
from dashboard.core.apis.schemas.requests.auth_request import LoginRequest
from dashboard.core.apis.schemas.responses.auth_response import AuthResponse
from dashboard.commons.auth import SESSION_COOKIE_NAME
from dashboard.core.apis.dependencies import get_auth_store
from dashboard.core.apis.dependencies import require_session

logging = logger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def _is_secure_request(request: Request) -> bool:
    """Return whether session cookies should use the Secure flag."""
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    return request.url.scheme == "https" or forwarded_proto.lower() == "https"


@auth_router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth_store=Depends(get_auth_store),
):
    """
    Create a dashboard session cookie.

    Args:
        payload: Dashboard login credentials.
        response: FastAPI response used to set the session cookie.

    Returns:
        AuthResponse: Login operation result.
    """
    try:
        logging.info("Calling POST /api/v1/auth/login endpoint username=%s", payload.username)
        if not auth_store.verify_password(payload.username, payload.password):
            logging.warning("Dashboard login failed username=%s", payload.username)
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
            secure=_is_secure_request(request),
            max_age=60 * 60 * DASHBOARD_SESSION_TTL_HOURS,
            path="/",
        )
        return AuthResponse(ok=True)
    except HTTPException as httperror:
        logging.error("Error in POST /api/v1/auth/login endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in POST /api/v1/auth/login endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@auth_router.post("/logout", response_model=AuthResponse)
def logout(
    response: Response,
    auth_store=Depends(get_auth_store),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    """
    Revoke the current dashboard session.

    Returns:
        AuthResponse: Logout operation result.
    """
    try:
        logging.info("Calling POST /api/v1/auth/logout endpoint")
        auth_store.revoke_session(session_token)
        response.delete_cookie(SESSION_COOKIE_NAME, path="/", samesite="strict")
        return AuthResponse(ok=True)
    except HTTPException as httperror:
        logging.error("Error in POST /api/v1/auth/logout endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in POST /api/v1/auth/logout endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@auth_router.post(
    "/password",
    response_model=AuthResponse,
    dependencies=[Depends(require_session)],
)
def change_password(
    payload: ChangePasswordRequest,
    auth_store=Depends(get_auth_store),
):
    """
    Change the dashboard login password.

    Args:
        payload: Password change request.

    Returns:
        AuthResponse: Password change operation result.
    """
    try:
        logging.info("Calling POST /api/v1/auth/password endpoint username=%s", payload.username)
        if not auth_store.change_password(
            payload.username, payload.current_password, payload.new_password
        ):
            logging.warning("Dashboard password change failed username=%s", payload.username)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        return AuthResponse(ok=True)
    except HTTPException as httperror:
        logging.error("Error in POST /api/v1/auth/password endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in POST /api/v1/auth/password endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
