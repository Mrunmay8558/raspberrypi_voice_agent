"""WiFi request schemas."""

from pydantic import BaseModel
from pydantic import Field


class WifiConnectRequest(BaseModel):
    """WiFi connect payload."""

    ssid: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=256)
