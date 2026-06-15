"""Remote voice response schemas."""

from pydantic import BaseModel
from pydantic import Field


class RemoteVoiceSettings(BaseModel):
    """Public remote voice settings shown in the dashboard."""

    runtime_mode: str = "local"
    public_api_base_url: str = ""
    daily_session_url: str = ""
    agent_id: str = ""
    conversation_metadata: dict = Field(default_factory=dict)
    dynamic_variables: dict = Field(default_factory=dict)
    conversation_visibility: bool = False
    conversation_config_type: str = "VOICE"
    is_test_call: bool = False
    client_type: str = "native"
    native_bin: str = ""
    native_config_file: str = ""
    api_key_configured: bool = False
    api_key_preview: str = ""
    restart_attempted: bool = False
    restart_succeeded: bool = False
    restart_message: str = ""


class SecretStatus(BaseModel):
    """Masked API key status."""

    configured: bool = False
    preview: str = ""


class ApiKeySettings(BaseModel):
    """Masked API key statuses for dashboard-managed secrets."""

    EIGI_API_KEY: SecretStatus
    OPENAI_API_KEY: SecretStatus
    DEEPGRAM_API_KEY: SecretStatus
    CARTESIA_API_KEY: SecretStatus
