"""Application configuration loader.

Configuration is resolved from, in order:

1. `.env` for secrets and deployment overrides.
2. ignored local `config.json` when present.
3. committed `config.example.json` as the default template.

Modules import constants from here so runtime code does not need to understand
where each value came from.
"""

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parent
LOCAL_CONFIG_FILE = PROJECT_ROOT / "config.json"
EXAMPLE_CONFIG_FILE = PROJECT_ROOT / "config.example.json"
DEFAULT_CONFIG_FILE = LOCAL_CONFIG_FILE if LOCAL_CONFIG_FILE.exists() else EXAMPLE_CONFIG_FILE
CONFIG_FILE = Path(os.getenv("APP_CONFIG_FILE", str(DEFAULT_CONFIG_FILE)))


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON configuration file.

    Args:
        path: File path to read.

    Returns:
        Parsed JSON object, or an empty object if the file does not exist.

    Raises:
        ValueError: If the file exists but is invalid JSON or not an object.
    """
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON config file: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON config file must contain an object: {path}")
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two dictionaries without mutating either input."""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _section(name: str) -> dict[str, Any]:
    """Return one top-level config section."""
    section = APP_CONFIG.get(name, {})
    if not isinstance(section, dict):
        raise ValueError(f"config.json section '{name}' must be an object.")
    return section


def _get(section: str, key: str, default: Any = None) -> Any:
    """Return one setting from a named config section."""
    return _section(section).get(key, default)


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment override."""
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{name} must be either 'true' or 'false'.")
    return normalized == "true"


def _env_int(name: str, default: int) -> int:
    """Read an integer environment override."""
    value = os.getenv(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def _env_float(name: str, default: float) -> float:
    """Read a floating-point environment override."""
    value = os.getenv(name, str(default))
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number.") from exc


def _path(value: str | Path) -> Path:
    """Resolve an absolute or project-relative path."""
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


APP_CONFIG = _read_json(CONFIG_FILE)

HERMES_CONFIG = _section("hermes")
VOICE_BOT_CONFIG = _section("voice_bot")
CLOUDFLARE_CONFIG = _section("cloudflare")
RUNTIME_CONFIG = _section("runtime")
WAKE_WORD_CONFIG = _section("wake_word")
AUDIO_CONFIG = _section("audio")
DASHBOARD_CONFIG = _section("dashboard")
REMOTE_VOICE_CONFIG = _section("remote_voice")
VOICE_CLIENT_CONFIG = _section("voice_client")


DEFAULT_HERMES_GATEWAY_COMMAND = os.getenv(
    "HERMES_GATEWAY_COMMAND",
    str(_get("hermes", "gateway_command", "hermes gateway run --replace")),
)
DEFAULT_HERMES_HOST = os.getenv("HERMES_HOST", str(_get("hermes", "host", "127.0.0.1")))
DEFAULT_HERMES_PORT = _env_int("HERMES_PORT", int(_get("hermes", "port", 8642)))

LOCAL_OPENAI_BASE_URL = str(
    _get(
        "voice_bot",
        "local_openai_base_url",
        f"http://{DEFAULT_HERMES_HOST}:{DEFAULT_HERMES_PORT}/v1",
    )
).format(host=DEFAULT_HERMES_HOST, port=DEFAULT_HERMES_PORT)
CLOUDFLARE_OPENAI_BASE_URL = str(
    _get("voice_bot", "cloudflare_openai_base_url", "https://your-tunnel.trycloudflare.com/v1")
)
LOCAL_VOICE_TESTING = _env_bool(
    "LOCAL_VOICE_TESTING", bool(_get("voice_bot", "local_voice_testing", True))
)
OPENAI_BASE_URL = LOCAL_OPENAI_BASE_URL if LOCAL_VOICE_TESTING else CLOUDFLARE_OPENAI_BASE_URL
DEFAULT_OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL", str(_get("voice_bot", "openai_model", "hermes-model"))
)
CARTESIA_VOICE_ID = str(_get("voice_bot", "cartesia_voice_id", ""))

DEFAULT_CLOUDFLARED_BIN = str(_get("cloudflare", "bin", "cloudflared"))
DEFAULT_CLOUDFLARED_WAIT_TIMEOUT_SECS = int(
    _get("cloudflare", "wait_timeout_secs", 90)
)
DEFAULT_CLOUDFLARED_QUICK_TUNNEL = str(_get("cloudflare", "quick_tunnel", "true"))
DEFAULT_CLOUDFLARED_TARGET_URL = str(
    _get("cloudflare", "target_url", f"http://localhost:{DEFAULT_HERMES_PORT}")
).format(port=DEFAULT_HERMES_PORT)

DEFAULT_PID_FILE = _path(str(_get("runtime", "pid_file", "run/bot.pid")))
VOICE_RUNTIME_MODE = os.getenv(
    "VOICE_RUNTIME_MODE", str(_get("runtime", "voice_runtime_mode", "local"))
).strip().lower()
if VOICE_RUNTIME_MODE not in {"local", "remote_daily"}:
    raise ValueError("VOICE_RUNTIME_MODE must be either 'local' or 'remote_daily'.")

DEFAULT_WAKEWORD_MODEL = os.getenv(
    "WAKEWORD_MODEL", str(_get("wake_word", "model", "hey jarvis"))
)
DEFAULT_THRESHOLD = _env_float("WAKEWORD_THRESHOLD", float(_get("wake_word", "threshold", 0.5)))
DEFAULT_COOLDOWN_SECS = _env_float(
    "WAKEWORD_COOLDOWN_SECS", float(_get("wake_word", "cooldown_secs", 8.0))
)
DEFAULT_VAD_THRESHOLD = _env_float(
    "WAKEWORD_VAD_THRESHOLD", float(_get("wake_word", "vad_threshold", 0.5))
)
DEFAULT_INFERENCE_FRAMEWORK = os.getenv(
    "WAKEWORD_INFERENCE_FRAMEWORK",
    str(_get("wake_word", "inference_framework", "onnx")),
)

SAMPLE_RATE = int(_get("audio", "sample_rate", 16000))
CHUNK_SIZE = int(_get("audio", "chunk_size", 1280))

DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", str(_get("dashboard", "host", "0.0.0.0")))
DASHBOARD_PORT = _env_int("DASHBOARD_PORT", int(_get("dashboard", "port", 8080)))
DASHBOARD_DEBUG = _env_bool("DASHBOARD_DEBUG", bool(_get("dashboard", "debug", False)))
DASHBOARD_DEFAULT_USERNAME = os.getenv(
    "DASHBOARD_DEFAULT_USERNAME",
    str(_get("dashboard", "default_username", "admin")),
)
DASHBOARD_SESSION_TTL_HOURS = _env_int(
    "DASHBOARD_SESSION_TTL_HOURS",
    int(_get("dashboard", "session_ttl_hours", 12)),
)
DASHBOARD_AUTH_FILE = _path(
    os.getenv("DASHBOARD_AUTH_FILE", str(_get("dashboard", "auth_file", "run/dashboard_auth.json")))
)
DASHBOARD_STATIC_DIR = _path(str(_get("dashboard", "static_dir", "dashboard/static")))

USER_CONFIG_FILE = _path(
    os.getenv("USER_CONFIG_FILE", str(_get("runtime", "user_config_file", "user.json")))
)
EIGI_API_KEY = os.getenv("EIGI_API_KEY", "").strip()

VOICE_CLIENT_TYPE = os.getenv(
    "VOICE_CLIENT_TYPE", str(_get("voice_client", "type", "native"))
).strip().lower()
if VOICE_CLIENT_TYPE != "native":
    raise ValueError("VOICE_CLIENT_TYPE must be 'native'.")
VOICE_CLIENT_HOST = os.getenv("VOICE_CLIENT_HOST", str(_get("voice_client", "host", "127.0.0.1"))).strip()
VOICE_CLIENT_PORT = _env_int("VOICE_CLIENT_PORT", int(_get("voice_client", "port", 8090)))
VOICE_CLIENT_NATIVE_BIN = os.getenv(
    "VOICE_CLIENT_NATIVE_BIN",
    str(_get("voice_client", "native_bin", "voice_client/native_daily/bin/pipecat-daily-client")),
).strip()
VOICE_CLIENT_NATIVE_CONFIG_FILE = os.getenv(
    "VOICE_CLIENT_NATIVE_CONFIG_FILE",
    str(_get("voice_client", "native_config_file", "voice_client/native_daily/config.json")),
).strip()
