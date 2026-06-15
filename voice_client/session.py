"""Create Eigi Daily sessions for the native remote voice client."""

import json
import urllib.error
import urllib.request
from typing import Any

from loguru import logger

from voice_client.config_store import RemoteVoiceConfig


class RemoteSessionError(RuntimeError):
    """Raised when an Eigi Daily session cannot be created."""

    pass


def create_daily_session(config: RemoteVoiceConfig) -> dict[str, Any]:
    """Create a Daily room/token session through Eigi public API.

    Args:
        config: Remote voice configuration including Eigi API key, selected
            agent, and Daily session URL.

    Returns:
        Eigi Daily session response with `room_url` and `token` aliases added
        for the native Daily C++ client.

    Raises:
        RemoteSessionError: If configuration is incomplete, the Eigi API returns
            an error, or the response is malformed.
    """
    if not config.daily_session_url:
        raise RemoteSessionError("daily_session_url is not configured in user.json.")
    if not config.api_key:
        raise RemoteSessionError("EIGI_API_KEY is not configured.")
    if not config.agent_id:
        raise RemoteSessionError("agent_id is not configured in user.json.")

    payload = _daily_session_payload(config)
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        config.daily_session_url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": config.api_key,
        },
    )

    logger.info("Creating remote Daily session via {}", config.daily_session_url)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RemoteSessionError(
            f"Daily session request failed with HTTP {exc.code}: {error_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RemoteSessionError(f"Daily session request failed: {exc}") from exc

    try:
        response_payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RemoteSessionError("Daily session response was not valid JSON.") from exc

    if not isinstance(response_payload, dict):
        raise RemoteSessionError("Daily session response must be a JSON object.")

    session = _normalize_daily_session(response_payload)
    if not session.get("dailyRoom") or not session.get("dailyToken"):
        raise RemoteSessionError("Daily session response missing dailyRoom/dailyToken.")
    logger.info(
        "Created remote Daily session conversation_id={}",
        session.get("conversation_id"),
    )
    return session


def _daily_session_payload(config: RemoteVoiceConfig) -> dict[str, Any]:
    """Build the Eigi `/v1/public/daily` request payload.

    Args:
        config: Fully resolved remote voice configuration.

    Returns:
        dict[str, Any]: JSON payload sent to the Eigi public Daily endpoint.
    """
    return {
        "agent_id": config.agent_id,
        "conversation_metadata": _conversation_metadata(config),
        "conversation_visibility": config.conversation_visibility,
        "conversation_config_type": config.conversation_config_type or "VOICE",
        "is_test_call": config.is_test_call,
    }


def _normalize_daily_session(session: dict[str, Any]) -> dict[str, Any]:
    """Add native-client field aliases to an Eigi Daily response.

    Args:
        session: Raw JSON session object returned by the Eigi API.

    Returns:
        dict[str, Any]: Session object with `room_url` and `token` aliases.
    """
    if "room_url" not in session and "dailyRoom" in session:
        session["room_url"] = session["dailyRoom"]
    if "token" not in session and "dailyToken" in session:
        session["token"] = session["dailyToken"]
    return session


def _conversation_metadata(config: RemoteVoiceConfig) -> dict[str, Any]:
    """Return conversation metadata with the selected agent ID included.

    Args:
        config: Fully resolved remote voice configuration.

    Returns:
        dict[str, Any]: Conversation metadata sent to the Daily endpoint.
    """
    metadata = dict(config.conversation_metadata or {})
    metadata["agent_id"] = config.agent_id
    return metadata
