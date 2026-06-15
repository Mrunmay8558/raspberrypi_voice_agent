"""Bluetooth routes for the dashboard API."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from dashboard.commons.logger import logger
from dashboard.core.apis.schemas.requests.bluetooth_request import BluetoothConnectRequest
from dashboard.core.apis.schemas.responses.bluetooth_response import BluetoothActionResponse
from dashboard.core.apis.schemas.responses.bluetooth_response import BluetoothDevice
from dashboard.core.controllers.bluetooth_controller import BluetoothController
from dashboard.core.apis.dependencies import require_session

logging = logger(__name__)

bluetooth_router = APIRouter(
    prefix="/api/bluetooth",
    tags=["bluetooth"],
    dependencies=[Depends(require_session)],
)


@bluetooth_router.get("/devices", response_model=list[BluetoothDevice])
def devices():
    """
    List known Bluetooth devices.

    Returns:
        list[BluetoothDevice]: Devices known to bluetoothctl.
    """
    try:
        logging.info("Calling GET /api/bluetooth/devices endpoint")
        return BluetoothController().list_devices()
    except HTTPException as httperror:
        logging.error("Error in GET /api/bluetooth/devices endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in GET /api/bluetooth/devices endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@bluetooth_router.post("/scan", response_model=list[BluetoothDevice])
def scan():
    """
    Scan for Bluetooth devices and return known devices.

    Returns:
        list[BluetoothDevice]: Devices visible after the scan.
    """
    try:
        logging.info("Calling POST /api/bluetooth/scan endpoint")
        return BluetoothController().scan_devices()
    except HTTPException as httperror:
        logging.error("Error in POST /api/bluetooth/scan endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in POST /api/bluetooth/scan endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@bluetooth_router.post("/connect", response_model=BluetoothActionResponse)
def connect(payload: BluetoothConnectRequest):
    """
    Pair, trust, and connect a Bluetooth device.

    Args:
        payload: Bluetooth connect request.

    Returns:
        BluetoothActionResponse: Command result.
    """
    try:
        logging.info("Calling POST /api/bluetooth/connect endpoint")
        return BluetoothController().connect_device(payload.mac, payload.pair, payload.trust)
    except HTTPException as httperror:
        logging.error("Error in POST /api/bluetooth/connect endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in POST /api/bluetooth/connect endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@bluetooth_router.post("/disconnect/{mac}", response_model=BluetoothActionResponse)
def disconnect(mac: str):
    """
    Disconnect a Bluetooth device.

    Args:
        mac: Bluetooth MAC address.

    Returns:
        BluetoothActionResponse: Command result.
    """
    try:
        logging.info("Calling POST /api/bluetooth/disconnect/%s endpoint", mac)
        return BluetoothController().disconnect_device(mac)
    except HTTPException as httperror:
        logging.error("Error in POST /api/bluetooth/disconnect endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in POST /api/bluetooth/disconnect endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
