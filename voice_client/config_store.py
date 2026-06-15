"""Load and persist remote voice client configuration.

Committed JSON files provide sanitized defaults. Runtime selections that can vary
per device are stored in ignored `user.json`; secrets remain in `.env`.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import REMOTE_VOICE_CONFIG
from config import USER_CONFIG_FILE
from config import VOICE_CLIENT_CONFIG
from config import VOICE_RUNTIME_MODE
from env_store import mask_secret
from env_store import read_secret
from env_store import write_env_values


@dataclass
class RemoteVoiceConfig:
    """Resolved configuration for remote Eigi voice sessions.

    Parameters:
        runtime_mode: Wake-listener runtime mode, `local` or `remote_daily`.
        public_api_base_url: Base URL for Eigi public APIs.
        daily_session_url: Eigi `/v1/public/daily` URL.
        api_key: Eigi API key loaded from `.env`.
        agent_id: Selected Eigi agent ID.
        conversation_metadata: Metadata sent to the Daily session endpoint.
        dynamic_variables: Runtime variables included in conversation metadata.
        conversation_visibility: Whether the created conversation is visible.
        conversation_config_type: Eigi conversation config type, usually `VOICE`.
        is_test_call: Whether Eigi should mark the session as a test call.
        client_type: Remote client implementation. Always `native`.
        native_bin: Native Daily client executable path.
        native_config_file: Native Daily client JSON config path.
    """

    runtime_mode: str = "local"
    public_api_base_url: str = ""
    daily_session_url: str = ""
    api_key: str = ""
    agent_id: str = ""
    conversation_metadata: dict[str, Any] | None = None
    dynamic_variables: dict[str, Any] | None = None
    conversation_visibility: bool = False
    conversation_config_type: str = "VOICE"
    is_test_call: bool = False
    client_type: str = "native"
    native_bin: str = ""
    native_config_file: str = ""


def load_remote_voice_config() -> RemoteVoiceConfig:
    """Load remote voice settings from defaults, user config, and `.env`.

    Returns:
        RemoteVoiceConfig: Fully resolved remote voice configuration.
    """
    file_config = _read_config_file(USER_CONFIG_FILE)
    remote_voice = _merge_section(REMOTE_VOICE_CONFIG, file_config.get("remote_voice", {}))
    voice_client = _merge_section(VOICE_CLIENT_CONFIG, file_config.get("voice_client", {}))
    runtime = file_config.get("runtime", {})
    if not isinstance(runtime, dict):
        runtime = {}

    # Backward compatibility for early flat config files.
    if not remote_voice:
        remote_voice = file_config

    public_api_base_url = str(
        remote_voice.get("public_api_base_url", _base_url_from_daily_url(remote_voice))
    ).strip()
    daily_session_url = str(remote_voice.get("daily_session_url", "")).strip()
    if not daily_session_url and public_api_base_url:
        daily_session_url = f"{public_api_base_url.rstrip('/')}/daily"

    config = RemoteVoiceConfig(
        runtime_mode=str(runtime.get("voice_runtime_mode", VOICE_RUNTIME_MODE)).strip().lower()
        or "local",
        api_key=read_secret("EIGI_API_KEY"),
        public_api_base_url=public_api_base_url,
        daily_session_url=daily_session_url,
        agent_id=str(remote_voice.get("agent_id", "")).strip(),
        conversation_metadata=_conversation_metadata(remote_voice),
        dynamic_variables=_dynamic_variables(remote_voice),
        conversation_visibility=bool(remote_voice.get("conversation_visibility", False)),
        conversation_config_type=str(
            remote_voice.get("conversation_config_type", "VOICE")
        ).strip()
        or "VOICE",
        is_test_call=bool(remote_voice.get("is_test_call", False)),
        client_type="native",
        native_bin=str(voice_client.get("native_bin", "")).strip(),
        native_config_file=str(voice_client.get("native_config_file", "")).strip(),
    )

    return config


def save_remote_voice_config(updates: dict[str, Any]) -> RemoteVoiceConfig:
    """Persist dashboard remote voice updates to ignored local config files.

    Args:
        updates: Partial remote voice settings from the dashboard.

    Returns:
        RemoteVoiceConfig: The resolved configuration after applying updates.
    """
    current = load_remote_voice_config()
    file_config = _read_config_file(USER_CONFIG_FILE)
    runtime = dict(file_config.get("runtime", {}))
    remote_voice = dict(file_config.get("remote_voice", {}))
    voice_client = dict(file_config.get("voice_client", {}))

    for key in (
        "public_api_base_url",
        "daily_session_url",
        "agent_id",
        "conversation_metadata",
        "dynamic_variables",
        "conversation_visibility",
        "conversation_config_type",
        "is_test_call",
    ):
        if key in updates and updates[key] is not None:
            if key in {"conversation_metadata", "dynamic_variables"}:
                remote_voice[key] = dict(updates[key])
            elif key in {"conversation_visibility", "is_test_call"}:
                remote_voice[key] = bool(updates[key])
            else:
                remote_voice[key] = str(updates[key]).strip()

    if "runtime_mode" in updates and updates["runtime_mode"] is not None:
        runtime_mode = str(updates["runtime_mode"]).strip().lower()
        if runtime_mode in {"local", "remote_daily"}:
            runtime["voice_runtime_mode"] = runtime_mode
            write_env_values({"VOICE_RUNTIME_MODE": runtime_mode})
    if "native_bin" in updates and updates["native_bin"] is not None:
        voice_client["native_bin"] = str(updates["native_bin"]).strip()
    if "native_config_file" in updates and updates["native_config_file"] is not None:
        voice_client["native_config_file"] = str(updates["native_config_file"]).strip()

    voice_client["type"] = "native"
    file_config["runtime"] = runtime
    file_config["remote_voice"] = remote_voice
    file_config["voice_client"] = voice_client

    try:
        USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        USER_CONFIG_FILE.write_text(json.dumps(file_config, indent=2))
        USER_CONFIG_FILE.chmod(0o600)
    except OSError as exc:
        raise RuntimeError(f"Failed to write user config: {USER_CONFIG_FILE}") from exc
    return current if not updates else load_remote_voice_config()


def public_remote_voice_config() -> dict[str, str | bool]:
    """Return remote voice settings safe for dashboard display.

    Returns:
        dict[str, str | bool]: Masked remote voice configuration for the
        dashboard UI.
    """
    config = load_remote_voice_config()
    return {
        "runtime_mode": config.runtime_mode,
        "public_api_base_url": config.public_api_base_url,
        "daily_session_url": config.daily_session_url,
        "agent_id": config.agent_id,
        "conversation_metadata": config.conversation_metadata or {},
        "dynamic_variables": config.dynamic_variables or {},
        "conversation_visibility": config.conversation_visibility,
        "conversation_config_type": config.conversation_config_type,
        "is_test_call": config.is_test_call,
        "client_type": "native",
        "native_bin": config.native_bin,
        "native_config_file": config.native_config_file,
        "api_key_configured": bool(config.api_key),
        "api_key_preview": mask_secret(config.api_key),
    }


def _read_config_file(path: Path) -> dict[str, Any]:
    """Read optional user config JSON.

    Invalid or unreadable user config is treated as absent so the dashboard can
    still boot and allow repair.

    Args:
        path: Path to the optional user configuration file.

    Returns:
        dict[str, Any]: Parsed JSON object, or an empty dict when the file is
        missing or unreadable.
    """
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _merge_section(defaults: dict[str, Any], overrides: Any) -> dict[str, Any]:
    """Merge one config section with shallow user overrides.

    Args:
        defaults: Committed or config-derived default values.
        overrides: User-provided override object.

    Returns:
        dict[str, Any]: Merged section values.
    """
    if not isinstance(overrides, dict):
        overrides = {}
    merged = dict(defaults)
    merged.update(overrides)
    return merged


def _conversation_metadata(remote_voice: dict[str, Any]) -> dict[str, Any]:
    """Build Eigi conversation metadata from stored remote voice settings.

    Args:
        remote_voice: Remote voice section loaded from configuration.

    Returns:
        dict[str, Any]: Conversation metadata with required agent and dynamic
        variable fields applied.
    """
    metadata = remote_voice.get("conversation_metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    agent_id = str(remote_voice.get("agent_id", "")).strip()
    if agent_id and not metadata.get("agent_id"):
        metadata["agent_id"] = agent_id
    dynamic_variables = _dynamic_variables(remote_voice)
    if dynamic_variables:
        metadata["dynamic_variables"] = dynamic_variables
    return metadata


def _dynamic_variables(remote_voice: dict[str, Any]) -> dict[str, Any]:
    """Extract dynamic variables from current or legacy config shapes.

    Args:
        remote_voice: Remote voice section loaded from configuration.

    Returns:
        dict[str, Any]: Resolved dynamic variables map.
    """
    value = remote_voice.get("dynamic_variables")
    if isinstance(value, dict):
        return value
    metadata = remote_voice.get("conversation_metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("dynamic_variables"), dict):
        return dict(metadata["dynamic_variables"])
    return {}


def _base_url_from_daily_url(remote_voice: dict[str, Any]) -> str:
    """Infer `/v1/public` base URL from a configured `/daily` URL.

    Args:
        remote_voice: Remote voice section loaded from configuration.

    Returns:
        str: Public API base URL derived from the stored settings.
    """
    daily_url = str(remote_voice.get("daily_session_url", "")).strip()
    if daily_url.endswith("/daily"):
        return daily_url[: -len("/daily")]
    return str(remote_voice.get("public_api_base_url", "")).strip()
