"""Utilities for reading and writing local environment secrets.

The dashboard uses this module to update `.env` without exposing secret values
back to the browser. Callers should return only masked previews to clients.
"""

from pathlib import Path

from dotenv import dotenv_values
from dotenv import set_key

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

SECRET_KEYS = (
    "EIGI_API_KEY",
    "OPENAI_API_KEY",
    "DEEPGRAM_API_KEY",
    "CARTESIA_API_KEY",
)


def read_env_values() -> dict[str, str]:
    """Read all configured values from the local `.env` file.

    Returns:
        Mapping of environment variable names to string values. Missing files
        produce an empty mapping.
    """
    values = dotenv_values(ENV_FILE)
    return {key: str(value or "") for key, value in values.items()}


def read_secret(name: str) -> str:
    """Read one secret from `.env`.

    Args:
        name: Environment variable name.

    Returns:
        The stripped secret value, or an empty string when unset.
    """
    return read_env_values().get(name, "").strip()


def write_env_values(updates: dict[str, str]) -> None:
    """Persist environment updates to `.env` with owner-only permissions.

    Args:
        updates: Environment variable names and values to write.
    """
    ENV_FILE.touch(mode=0o600, exist_ok=True)
    for key, value in updates.items():
        set_key(str(ENV_FILE), key, value or "", quote_mode="never")
    ENV_FILE.chmod(0o600)


def mask_secret(value: str) -> str:
    """Return a non-sensitive preview for a secret value."""
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def public_secret_status() -> dict[str, dict[str, str | bool]]:
    """Return masked configuration status for dashboard clients."""
    return {
        key: {
            "configured": bool(value := read_secret(key)),
            "preview": mask_secret(value),
        }
        for key in SECRET_KEYS
    }
