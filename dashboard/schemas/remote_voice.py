from pydantic import BaseModel
from pydantic import Field


class RemoteVoiceSettings(BaseModel):
    runtime_mode: str = "local"
    public_api_base_url: str = ""
    daily_session_url: str = ""
    agent_id: str = ""
    conversation_metadata: dict = {}
    dynamic_variables: dict = {}
    conversation_visibility: bool = False
    conversation_config_type: str = "VOICE"
    is_test_call: bool = False
    client_type: str = "native"
    native_bin: str = ""
    native_config_file: str = ""
    api_key_configured: bool = False
    api_key_preview: str = ""


class RemoteVoiceSettingsUpdate(BaseModel):
    runtime_mode: str | None = Field(default=None, max_length=32)
    public_api_base_url: str | None = Field(default=None, max_length=512)
    daily_session_url: str | None = Field(default=None, max_length=512)
    agent_id: str | None = Field(default=None, max_length=128)
    conversation_metadata: dict | None = None
    dynamic_variables: dict | None = None
    conversation_visibility: bool | None = None
    conversation_config_type: str | None = Field(default=None, max_length=16)
    is_test_call: bool | None = None
    native_bin: str | None = Field(default=None, max_length=512)
    native_config_file: str | None = Field(default=None, max_length=512)


class SecretStatus(BaseModel):
    configured: bool = False
    preview: str = ""


class ApiKeySettings(BaseModel):
    EIGI_API_KEY: SecretStatus
    OPENAI_API_KEY: SecretStatus
    DEEPGRAM_API_KEY: SecretStatus
    CARTESIA_API_KEY: SecretStatus


class ApiKeySettingsUpdate(BaseModel):
    EIGI_API_KEY: str | None = Field(default=None, max_length=2048)
    OPENAI_API_KEY: str | None = Field(default=None, max_length=2048)
    DEEPGRAM_API_KEY: str | None = Field(default=None, max_length=2048)
    CARTESIA_API_KEY: str | None = Field(default=None, max_length=2048)
