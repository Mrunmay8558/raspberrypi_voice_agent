from fastapi import APIRouter
from fastapi import Depends

from dashboard.dependencies import require_session
from dashboard.schemas.remote_voice import RemoteVoiceSettings
from dashboard.schemas.remote_voice import RemoteVoiceSettingsUpdate
from voice_client.config_store import public_remote_voice_config
from voice_client.config_store import save_remote_voice_config

router = APIRouter(
    prefix="/api/remote-voice",
    tags=["remote-voice"],
    dependencies=[Depends(require_session)],
)


@router.get("/settings", response_model=RemoteVoiceSettings)
def get_settings():
    return public_remote_voice_config()


@router.put("/settings", response_model=RemoteVoiceSettings)
def update_settings(payload: RemoteVoiceSettingsUpdate):
    updates = payload.model_dump(exclude_unset=True)
    save_remote_voice_config(updates)
    return public_remote_voice_config()
