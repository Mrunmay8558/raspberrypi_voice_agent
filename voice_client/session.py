import json
import urllib.error
import urllib.request
from typing import Any

from loguru import logger

from voice_client.config_store import RemoteVoiceConfig


class RemoteSessionError(RuntimeError):
    pass


def create_daily_session(config: RemoteVoiceConfig) -> dict[str, Any]:
    if not config.daily_session_url:
        raise RemoteSessionError("daily_session_url is not configured in user.json.")
    if not config.api_key:
        raise RemoteSessionError("EIGI_API_KEY is not configured.")
    if not config.agent_id:
        raise RemoteSessionError("agent_id is not configured in user.json.")

    payload = {
        "agent_id": config.agent_id,
        "conversation_metadata": _conversation_metadata(config),
        "conversation_visibility": config.conversation_visibility,
        "conversation_config_type": config.conversation_config_type or "VOICE",
        "is_test_call": config.is_test_call,
    }
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

    session = _normalize_daily_session(json.loads(body))
    if not session.get("dailyRoom") or not session.get("dailyToken"):
        raise RemoteSessionError("Daily session response missing dailyRoom/dailyToken.")
    logger.info("Created remote Daily session conversation_id={}", session.get("conversation_id"))
    return session


def _normalize_daily_session(session: dict[str, Any]) -> dict[str, Any]:
    if "room_url" not in session and "dailyRoom" in session:
        session["room_url"] = session["dailyRoom"]
    if "token" not in session and "dailyToken" in session:
        session["token"] = session["dailyToken"]
    return session


def _conversation_metadata(config: RemoteVoiceConfig) -> dict[str, Any]:
    metadata = dict(config.conversation_metadata or {})
    metadata["agent_id"] = config.agent_id
    return metadata
