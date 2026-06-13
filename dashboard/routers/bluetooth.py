from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from dashboard.dependencies import require_session
from dashboard.schemas.bluetooth import BluetoothActionResponse
from dashboard.schemas.bluetooth import BluetoothConnectRequest
from dashboard.schemas.bluetooth import BluetoothDevice
from dashboard.services import bluetooth_service
from dashboard.services.command_service import CommandError

router = APIRouter(
    prefix="/api/bluetooth",
    tags=["bluetooth"],
    dependencies=[Depends(require_session)],
)


@router.get("/devices", response_model=list[BluetoothDevice])
def devices():
    return bluetooth_service.list_devices()


@router.post("/scan", response_model=list[BluetoothDevice])
def scan():
    return bluetooth_service.scan_devices()


@router.post("/connect", response_model=BluetoothActionResponse)
def connect(payload: BluetoothConnectRequest):
    try:
        output = bluetooth_service.connect_device(payload.mac, payload.pair, payload.trust)
    except CommandError as exc:
        raise HTTPException(status_code=400, detail=exc.output) from exc
    return BluetoothActionResponse(ok=True, output=output)


@router.post("/disconnect/{mac}", response_model=BluetoothActionResponse)
def disconnect(mac: str):
    try:
        output = bluetooth_service.disconnect_device(mac)
    except CommandError as exc:
        raise HTTPException(status_code=400, detail=exc.output) from exc
    return BluetoothActionResponse(ok=True, output=output)
