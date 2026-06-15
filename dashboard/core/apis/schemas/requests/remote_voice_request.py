"""Remote voice request schemas."""

from pydantic import BaseModel
from pydantic import Field


class RemoteVoiceSettingsUpdate(BaseModel):
    """Partial remote voice settings update payload."""

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


class ApiKeySettingsUpdate(BaseModel):
    """Dashboard-managed API key update payload."""

    EIGI_API_KEY: str | None = Field(default=None, max_length=2048)
    OPENAI_API_KEY: str | None = Field(default=None, max_length=2048)
    DEEPGRAM_API_KEY: str | None = Field(default=None, max_length=2048)
    CARTESIA_API_KEY: str | None = Field(default=None, max_length=2048)
