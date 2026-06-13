from pydantic import BaseModel
from pydantic import Field


class BluetoothDevice(BaseModel):
    mac: str
    name: str
    connected: bool = False
    paired: bool = False
    trusted: bool = False


class BluetoothConnectRequest(BaseModel):
    mac: str = Field(min_length=8, max_length=32)
    pair: bool = True
    trust: bool = True


class BluetoothActionResponse(BaseModel):
    ok: bool
    output: str
