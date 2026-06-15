from pydantic import BaseModel
from pydantic import Field


class RemoteVoiceSettings(BaseModel):
    daily_session_url: str = ""
    agent_id: str = ""
    conversation_metadata: dict = {}
    conversation_visibility: bool = False
    conversation_config_type: str = "VOICE"
    client_type: str = "native"
    native_bin: str = ""
    native_config_file: str = ""
    api_key_configured: bool = False
    api_key_preview: str = ""


class RemoteVoiceSettingsUpdate(BaseModel):
    daily_session_url: str | None = Field(default=None, max_length=512)
    agent_id: str | None = Field(default=None, max_length=128)
    conversation_metadata: dict | None = None
    conversation_visibility: bool | None = None
    conversation_config_type: str | None = Field(default=None, max_length=16)
    client_type: str | None = Field(default=None, max_length=16)
    native_bin: str | None = Field(default=None, max_length=512)
    native_config_file: str | None = Field(default=None, max_length=512)
