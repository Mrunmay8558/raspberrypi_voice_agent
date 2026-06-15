"""WiFi response schemas."""

from pydantic import BaseModel


class WifiNetwork(BaseModel):
    """Detected WiFi network."""

    ssid: str
    signal: int | None = None
    security: str | None = None
    active: bool = False


class WifiConnectResponse(BaseModel):
    """WiFi connection result."""

    ok: bool
    output: str
