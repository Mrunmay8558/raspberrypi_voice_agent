from fastapi import APIRouter
from fastapi import Depends

from dashboard.dependencies import require_session
from dashboard.schemas.system import SystemStatus
from dashboard.services.system_service import get_status

router = APIRouter(
    prefix="/api/system",
    tags=["system"],
    dependencies=[Depends(require_session)],
)


@router.get("/status", response_model=SystemStatus)
def status():
    return get_status()
