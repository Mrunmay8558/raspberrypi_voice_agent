import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from dashboard.dependencies import require_session
from dashboard.schemas.remote_voice import ApiKeySettings
from dashboard.schemas.remote_voice import ApiKeySettingsUpdate
from dashboard.schemas.remote_voice import RemoteVoiceSettings
from dashboard.schemas.remote_voice import RemoteVoiceSettingsUpdate
from env_store import public_secret_status
from env_store import read_secret
from env_store import write_env_values
from voice_client.config_store import public_remote_voice_config
from voice_client.config_store import save_remote_voice_config

router = APIRouter(
    prefix="/api/remote-voice",
    tags=["remote-voice"],
    dependencies=[Depends(require_session)],
)


@router.get("/settings", response_model=RemoteVoiceSettings)
def get_settings():
    return public_remote_voice_config()


@router.put("/settings", response_model=RemoteVoiceSettings)
def update_settings(payload: RemoteVoiceSettingsUpdate):
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("public_api_base_url") and not updates.get("daily_session_url"):
        updates["daily_session_url"] = _daily_url(updates["public_api_base_url"])
    save_remote_voice_config(updates)
    return public_remote_voice_config()


@router.get("/api-keys", response_model=ApiKeySettings)
def get_api_keys():
    return public_secret_status()


@router.put("/api-keys", response_model=ApiKeySettings)
def update_api_keys(payload: ApiKeySettingsUpdate):
    updates = {
        key: value.strip()
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None and value.strip()
    }
    if updates:
        write_env_values(updates)
    return public_secret_status()


@router.get("/agents")
def list_agents(page: int = 1, page_size: int = 100, search: str | None = None):
    settings = public_remote_voice_config()
    base_url = settings.get("public_api_base_url") or _base_url(settings.get("daily_session_url", ""))
    query = {"page": str(page), "page_size": str(page_size)}
    if search:
        query["search"] = search
    return _eigi_request(f"{base_url.rstrip('/')}/agents?{urllib.parse.urlencode(query)}")


@router.get("/agents/{agent_id}/dynamic-variables")
def get_agent_dynamic_variables(agent_id: str):
    settings = public_remote_voice_config()
    base_url = settings.get("public_api_base_url") or _base_url(settings.get("daily_session_url", ""))
    return _eigi_request(f"{base_url.rstrip('/')}/agents/{agent_id}/dynamic-variables")


def _eigi_request(url: str) -> dict[str, Any]:
    api_key = read_secret("EIGI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="EIGI_API_KEY is not configured.")
    request = urllib.request.Request(url, headers={"X-API-Key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail) from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Eigi API request failed: {exc}") from exc


def _base_url(daily_session_url: str) -> str:
    if daily_session_url.endswith("/daily"):
        return daily_session_url[: -len("/daily")]
    return daily_session_url


def _daily_url(public_api_base_url: str) -> str:
    return f"{public_api_base_url.rstrip('/')}/daily"
