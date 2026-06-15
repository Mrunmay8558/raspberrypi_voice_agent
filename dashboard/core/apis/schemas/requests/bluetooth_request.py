"""Bluetooth request schemas."""

from pydantic import BaseModel
from pydantic import Field


class BluetoothConnectRequest(BaseModel):
    """Bluetooth connect payload."""

    mac: str = Field(min_length=8, max_length=32)
    pair: bool = True
    trust: bool = True
