"""Bluetooth response schemas."""

from pydantic import BaseModel


class BluetoothDevice(BaseModel):
    """Bluetooth device details returned by bluetoothctl."""

    mac: str
    name: str
    connected: bool = False
    paired: bool = False
    trusted: bool = False


class BluetoothActionResponse(BaseModel):
    """Bluetooth command result."""

    ok: bool
    output: str
