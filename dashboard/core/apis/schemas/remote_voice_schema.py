"""Compatibility exports for dashboard remote voice schemas."""

from dashboard.core.apis.schemas.requests.remote_voice_request import ApiKeySettingsUpdate
from dashboard.core.apis.schemas.requests.remote_voice_request import RemoteVoiceSettingsUpdate
from dashboard.core.apis.schemas.responses.remote_voice_response import ApiKeySettings
from dashboard.core.apis.schemas.responses.remote_voice_response import RemoteVoiceSettings

__all__ = [
    "ApiKeySettings",
    "ApiKeySettingsUpdate",
    "RemoteVoiceSettings",
    "RemoteVoiceSettingsUpdate",
]
