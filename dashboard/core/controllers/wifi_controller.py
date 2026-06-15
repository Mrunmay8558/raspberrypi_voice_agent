"""Business logic layer for dashboard WiFi operations.

This controller translates WiFi configuration requests into service calls and
normalizes command failures into HTTP-safe errors for the API layer.
"""

from fastapi import HTTPException

from dashboard.commons.logger import logger
from dashboard.core.apis.schemas.responses.wifi_response import WifiConnectResponse
from dashboard.core.apis.schemas.responses.wifi_response import WifiNetwork
from dashboard.core.services import wifi_service
from dashboard.core.services.command_service import CommandError

logging = logger(__name__)


class WifiController:
    """Coordinate WiFi service calls and command error handling."""

    def scan_networks(self) -> list[WifiNetwork]:
        """Return visible WiFi networks ordered by signal strength.

        Returns:
            list[WifiNetwork]: Nearby WiFi networks discovered by NetworkManager.
        """
        logging.info("WifiController.scan_networks")
        return wifi_service.scan_networks()

    def connect_network(self, ssid: str, password: str) -> WifiConnectResponse:
        """Connect to a WiFi network through NetworkManager.

        Args:
            ssid: WiFi network name.
            password: WiFi password.

        Returns:
            WifiConnectResponse: Command output for the connection attempt.

        Raises:
            HTTPException: Raised when the underlying command fails.
        """
        logging.info("WifiController.connect_network ssid=%s", ssid)
        try:
            output = wifi_service.connect_network(ssid, password)
        except CommandError as exc:
            logging.error("WiFi connect failed ssid=%s output=%s", ssid, exc.output)
            raise HTTPException(status_code=400, detail=exc.output) from exc
        return WifiConnectResponse(ok=True, output=output)
