"""Business logic layer for dashboard Bluetooth operations.

This controller translates route-level Bluetooth requests into service calls
and converts command failures into HTTP-safe errors for the API layer.
"""

from fastapi import HTTPException

from dashboard.core import logger
from dashboard.core.apis.schemas.responses.bluetooth_response import BluetoothActionResponse
from dashboard.core.apis.schemas.responses.bluetooth_response import BluetoothDevice
from dashboard.core.services import bluetooth_service
from dashboard.core.services.command_service import CommandError

logging = logger(__name__)


class BluetoothController:
    """Coordinate Bluetooth service calls and command error handling."""

    def list_devices(self) -> list[BluetoothDevice]:
        """Return Bluetooth devices known to the current host.

        Returns:
            list[BluetoothDevice]: Devices reported by `bluetoothctl devices`.
        """
        logging.info("BluetoothController.list_devices")
        return bluetooth_service.list_devices()

    def scan_devices(self) -> list[BluetoothDevice]:
        """Scan for nearby Bluetooth devices.

        Returns:
            list[BluetoothDevice]: Devices visible after a scan cycle.
        """
        logging.info("BluetoothController.scan_devices")
        return bluetooth_service.scan_devices()

    def connect_device(
        self,
        mac: str,
        pair: bool = True,
        trust: bool = True,
    ) -> BluetoothActionResponse:
        """Pair, trust, and connect a Bluetooth device.

        Args:
            mac: Bluetooth MAC address.
            pair: Whether the device should be paired before connecting.
            trust: Whether the device should be trusted before connecting.

        Returns:
            BluetoothActionResponse: Command output for the connection flow.

        Raises:
            HTTPException: Raised when the underlying command fails.
        """
        logging.info("BluetoothController.connect_device mac=%s", mac)
        try:
            output = bluetooth_service.connect_device(mac, pair, trust)
        except CommandError as exc:
            logging.error("Bluetooth connect failed mac=%s output=%s", mac, exc.output)
            raise HTTPException(status_code=400, detail=exc.output) from exc
        return BluetoothActionResponse(ok=True, output=output)

    def disconnect_device(self, mac: str) -> BluetoothActionResponse:
        """Disconnect a Bluetooth device.

        Args:
            mac: Bluetooth MAC address.

        Returns:
            BluetoothActionResponse: Command output for the disconnect action.

        Raises:
            HTTPException: Raised when the underlying command fails.
        """
        logging.info("BluetoothController.disconnect_device mac=%s", mac)
        try:
            output = bluetooth_service.disconnect_device(mac)
        except CommandError as exc:
            logging.error("Bluetooth disconnect failed mac=%s output=%s", mac, exc.output)
            raise HTTPException(status_code=400, detail=exc.output) from exc
        return BluetoothActionResponse(ok=True, output=output)
