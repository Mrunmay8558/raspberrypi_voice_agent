"""WiFi routes for the dashboard API."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from dashboard.core import logger
from dashboard.core.apis.schemas.requests.wifi_request import WifiConnectRequest
from dashboard.core.apis.schemas.responses.wifi_response import WifiConnectResponse
from dashboard.core.apis.schemas.responses.wifi_response import WifiNetwork
from dashboard.core.controllers.wifi_controller import WifiController
from dashboard.core.apis.dependencies import require_session

logging = logger(__name__)

wifi_router = APIRouter(
    prefix="/wifi",
    tags=["wifi"],
    dependencies=[Depends(require_session)],
)


@wifi_router.get("/networks", response_model=list[WifiNetwork])
def networks():
    """
    Scan available WiFi networks.

    Returns:
        list[WifiNetwork]: Visible networks ordered by signal strength.
    """
    try:
        logging.info("Calling GET /api/v1/wifi/networks endpoint")
        return WifiController().scan_networks()
    except HTTPException as httperror:
        logging.error("Error in GET /api/v1/wifi/networks endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in GET /api/v1/wifi/networks endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@wifi_router.post("/connect", response_model=WifiConnectResponse)
def connect(payload: WifiConnectRequest):
    """
    Connect to a WiFi network through NetworkManager.

    Args:
        payload: WiFi credentials.

    Returns:
        WifiConnectResponse: Command result.
    """
    try:
        logging.info("Calling POST /api/v1/wifi/connect endpoint")
        return WifiController().connect_network(payload.ssid, payload.password)
    except HTTPException as httperror:
        logging.error("Error in POST /api/v1/wifi/connect endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in POST /api/v1/wifi/connect endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
