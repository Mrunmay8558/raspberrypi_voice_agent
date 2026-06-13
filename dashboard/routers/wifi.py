from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from dashboard.dependencies import require_session
from dashboard.schemas.wifi import WifiConnectRequest
from dashboard.schemas.wifi import WifiConnectResponse
from dashboard.schemas.wifi import WifiNetwork
from dashboard.services.command_service import CommandError
from dashboard.services import wifi_service

router = APIRouter(
    prefix="/api/wifi",
    tags=["wifi"],
    dependencies=[Depends(require_session)],
)


@router.get("/networks", response_model=list[WifiNetwork])
def networks():
    return wifi_service.scan_networks()


@router.post("/connect", response_model=WifiConnectResponse)
def connect(payload: WifiConnectRequest):
    try:
        output = wifi_service.connect_network(payload.ssid, payload.password)
    except CommandError as exc:
        raise HTTPException(status_code=400, detail=exc.output) from exc
    return WifiConnectResponse(ok=True, output=output)
