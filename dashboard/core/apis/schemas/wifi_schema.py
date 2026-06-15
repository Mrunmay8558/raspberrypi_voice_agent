"""Compatibility exports for dashboard WiFi schemas."""

from dashboard.core.apis.schemas.requests.wifi_request import WifiConnectRequest
from dashboard.core.apis.schemas.responses.wifi_response import WifiConnectResponse
from dashboard.core.apis.schemas.responses.wifi_response import WifiNetwork

__all__ = ["WifiConnectRequest", "WifiConnectResponse", "WifiNetwork"]
