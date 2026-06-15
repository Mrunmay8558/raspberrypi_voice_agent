"""Compatibility exports for dashboard Bluetooth schemas."""

from dashboard.core.apis.schemas.requests.bluetooth_request import BluetoothConnectRequest
from dashboard.core.apis.schemas.responses.bluetooth_response import BluetoothActionResponse
from dashboard.core.apis.schemas.responses.bluetooth_response import BluetoothDevice

__all__ = ["BluetoothActionResponse", "BluetoothConnectRequest", "BluetoothDevice"]
