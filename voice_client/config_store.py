import json
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import EIGI_API_KEY
from config import REMOTE_VOICE_CONFIG
from config import USER_CONFIG_FILE
from config import VOICE_CLIENT_CONFIG


@dataclass
class RemoteVoiceConfig:
    daily_session_url: str = ""
    api_key: str = ""
    agent_id: str = ""
    conversation_metadata: dict[str, Any] | None = None
    conversation_visibility: bool = False
    conversation_config_type: str = "VOICE"
    client_type: str = "native"
    native_bin: str = ""
    native_config_file: str = ""


def load_remote_voice_config() -> RemoteVoiceConfig:
    file_config = _read_config_file(USER_CONFIG_FILE)
    remote_voice = _merge_section(REMOTE_VOICE_CONFIG, file_config.get("remote_voice", {}))
    voice_client = _merge_section(VOICE_CLIENT_CONFIG, file_config.get("voice_client", {}))

    # Backward compatibility for early flat config files.
    if not remote_voice:
        remote_voice = file_config

    config = RemoteVoiceConfig(
        api_key=EIGI_API_KEY,
        daily_session_url=str(remote_voice.get("daily_session_url", "")).strip(),
        agent_id=str(remote_voice.get("agent_id", "")).strip(),
        conversation_metadata=_conversation_metadata(remote_voice),
        conversation_visibility=bool(remote_voice.get("conversation_visibility", False)),
        conversation_config_type=str(
            remote_voice.get("conversation_config_type", "VOICE")
        ).strip()
        or "VOICE",
        client_type=str(voice_client.get("type", "native")).strip().lower() or "native",
        native_bin=str(voice_client.get("native_bin", "")).strip(),
        native_config_file=str(voice_client.get("native_config_file", "")).strip(),
    )

    return config


def save_remote_voice_config(updates: dict[str, Any]) -> RemoteVoiceConfig:
    current = load_remote_voice_config()
    file_config = _read_config_file(USER_CONFIG_FILE)
    remote_voice = dict(file_config.get("remote_voice", {}))
    voice_client = dict(file_config.get("voice_client", {}))

    for key in (
        "daily_session_url",
        "agent_id",
        "conversation_metadata",
        "conversation_visibility",
        "conversation_config_type",
    ):
        if key in updates and updates[key] is not None:
            if key == "conversation_metadata":
                remote_voice[key] = dict(updates[key])
            elif key == "conversation_visibility":
                remote_voice[key] = bool(updates[key])
            else:
                remote_voice[key] = str(updates[key]).strip()

    if "client_type" in updates and updates["client_type"] is not None:
        voice_client["type"] = str(updates["client_type"]).strip().lower()
    if "native_bin" in updates and updates["native_bin"] is not None:
        voice_client["native_bin"] = str(updates["native_bin"]).strip()
    if "native_config_file" in updates and updates["native_config_file"] is not None:
        voice_client["native_config_file"] = str(updates["native_config_file"]).strip()

    file_config["remote_voice"] = remote_voice
    file_config["voice_client"] = voice_client

    USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    USER_CONFIG_FILE.write_text(json.dumps(file_config, indent=2))
    USER_CONFIG_FILE.chmod(0o600)
    return current if not updates else load_remote_voice_config()


def public_remote_voice_config() -> dict[str, str | bool]:
    config = load_remote_voice_config()
    return {
        "daily_session_url": config.daily_session_url,
        "agent_id": config.agent_id,
        "conversation_metadata": config.conversation_metadata or {},
        "conversation_visibility": config.conversation_visibility,
        "conversation_config_type": config.conversation_config_type,
        "client_type": config.client_type,
        "native_bin": config.native_bin,
        "native_config_file": config.native_config_file,
        "api_key_configured": bool(config.api_key),
        "api_key_preview": _mask_secret(config.api_key),
    }


def _read_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _merge_section(defaults: dict[str, Any], overrides: Any) -> dict[str, Any]:
    if not isinstance(overrides, dict):
        overrides = {}
    merged = dict(defaults)
    merged.update(overrides)
    return merged


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def _conversation_metadata(remote_voice: dict[str, Any]) -> dict[str, Any]:
    metadata = remote_voice.get("conversation_metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    agent_id = str(remote_voice.get("agent_id", "")).strip()
    if agent_id and not metadata.get("agent_id"):
        metadata["agent_id"] = agent_id
    return metadata
