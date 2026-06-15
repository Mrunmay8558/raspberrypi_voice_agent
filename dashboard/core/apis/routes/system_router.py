"""System routes for the dashboard API."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from dashboard.commons.logger import logger
from dashboard.core.apis.schemas.responses.system_response import SystemStatus
from dashboard.core.controllers.system_controller import SystemController
from dashboard.core.apis.dependencies import require_session

logging = logger(__name__)

system_router = APIRouter(
    prefix="/api/system",
    tags=["system"],
    dependencies=[Depends(require_session)],
)


@system_router.get("/status", response_model=SystemStatus)
def status():
    """
    Return host and systemd service status.

    Returns:
        SystemStatus: Hostname, local dashboard URL, and service states.
    """
    try:
        logging.info("Calling GET /api/system/status endpoint")
        return SystemController().get_status()
    except HTTPException as httperror:
        logging.error("Error in GET /api/system/status endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in GET /api/system/status endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
