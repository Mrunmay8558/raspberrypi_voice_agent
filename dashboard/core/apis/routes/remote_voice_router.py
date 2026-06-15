"""Remote voice routes for the dashboard API."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from dashboard.core import logger
from dashboard.core.apis.schemas.requests.remote_voice_request import ApiKeySettingsUpdate
from dashboard.core.apis.schemas.requests.remote_voice_request import RemoteVoiceSettingsUpdate
from dashboard.core.apis.schemas.responses.remote_voice_response import ApiKeySettings
from dashboard.core.apis.schemas.responses.remote_voice_response import RemoteVoiceSettings
from dashboard.core.controllers.remote_voice_controller import RemoteVoiceController
from dashboard.core.apis.dependencies import require_session

logging = logger(__name__)

remote_voice_router = APIRouter(
    prefix="/remote-voice",
    tags=["remote-voice"],
    dependencies=[Depends(require_session)],
)


@remote_voice_router.get("/settings", response_model=RemoteVoiceSettings)
def get_settings():
    """
    Return current voice runtime settings for the dashboard.

    Returns:
        RemoteVoiceSettings: Public remote voice configuration.
    """
    try:
        logging.info("Calling GET /api/remote-voice/settings endpoint")
        return RemoteVoiceController().get_settings()
    except HTTPException as httperror:
        logging.error("Error in GET /api/remote-voice/settings endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in GET /api/remote-voice/settings endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@remote_voice_router.put("/settings", response_model=RemoteVoiceSettings)
def update_settings(payload: RemoteVoiceSettingsUpdate):
    """
    Persist voice runtime settings from the dashboard.

    Args:
        payload: Partial remote voice settings update.

    Returns:
        RemoteVoiceSettings: Settings after persistence.
    """
    try:
        logging.info("Calling PUT /api/remote-voice/settings endpoint")
        return RemoteVoiceController().update_settings(payload.model_dump(exclude_unset=True))
    except HTTPException as httperror:
        logging.error("Error in PUT /api/remote-voice/settings endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in PUT /api/remote-voice/settings endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@remote_voice_router.get("/api-keys", response_model=ApiKeySettings)
def get_api_keys():
    """
    Return masked status for dashboard-managed API keys.

    Returns:
        ApiKeySettings: Masked configured states.
    """
    try:
        logging.info("Calling GET /api/remote-voice/api-keys endpoint")
        return RemoteVoiceController().get_api_keys()
    except HTTPException as httperror:
        logging.error("Error in GET /api/remote-voice/api-keys endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in GET /api/remote-voice/api-keys endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@remote_voice_router.put("/api-keys", response_model=ApiKeySettings)
def update_api_keys(payload: ApiKeySettingsUpdate):
    """
    Persist API key updates to `.env`.

    Args:
        payload: API keys to update. Empty values are ignored.

    Returns:
        ApiKeySettings: Masked configured states after persistence.
    """
    try:
        logging.info("Calling PUT /api/remote-voice/api-keys endpoint")
        return RemoteVoiceController().update_api_keys(payload.model_dump(exclude_unset=True))
    except HTTPException as httperror:
        logging.error("Error in PUT /api/remote-voice/api-keys endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in PUT /api/remote-voice/api-keys endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@remote_voice_router.get("/agents")
def list_agents(page: int = 1, page_size: int = 100, search: str | None = None):
    """
    List Eigi agents visible to the configured public API key.

    Args:
        page: Page number.
        page_size: Number of agents per page.
        search: Optional search query.

    Returns:
        dict: Response from the configured Eigi public API.
    """
    try:
        logging.info("Calling GET /api/remote-voice/agents endpoint")
        return RemoteVoiceController().list_agents(page=page, page_size=page_size, search=search)
    except HTTPException as httperror:
        logging.error("Error in GET /api/remote-voice/agents endpoint: %s", httperror)
        raise httperror
    except Exception as error:
        logging.error("Error in GET /api/remote-voice/agents endpoint: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@remote_voice_router.get("/agents/{agent_id}/dynamic-variables")
def get_agent_dynamic_variables(agent_id: str):
    """
    Return dynamic variable definitions for one Eigi agent.

    Args:
        agent_id: Eigi agent ID.

    Returns:
        dict: Dynamic variable response from the configured Eigi public API.
    """
    try:
        logging.info("Calling GET /api/remote-voice/agents/%s/dynamic-variables endpoint", agent_id)
        return RemoteVoiceController().get_agent_dynamic_variables(agent_id)
    except HTTPException as httperror:
        logging.error(
            "Error in GET /api/remote-voice/agents/%s/dynamic-variables endpoint: %s",
            agent_id,
            httperror,
        )
        raise httperror
    except Exception as error:
        logging.error(
            "Error in GET /api/remote-voice/agents/%s/dynamic-variables endpoint: %s",
            agent_id,
            error,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
