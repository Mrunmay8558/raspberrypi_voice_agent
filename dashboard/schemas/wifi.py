from pydantic import BaseModel
from pydantic import Field


class WifiNetwork(BaseModel):
    ssid: str
    signal: int | None = None
    security: str | None = None
    active: bool = False


class WifiConnectRequest(BaseModel):
    ssid: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=256)


class WifiConnectResponse(BaseModel):
    ok: bool
    output: str
