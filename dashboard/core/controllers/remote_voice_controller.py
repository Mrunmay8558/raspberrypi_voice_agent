"""Business logic layer for dashboard remote voice configuration.

This controller manages persisted remote-voice settings, dashboard-managed
API keys, and read-only calls to the Eigi public API.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException

from dashboard.core import logger
from env_store import public_secret_status
from env_store import read_secret
from env_store import write_env_values
from voice_client.config_store import public_remote_voice_config
from voice_client.config_store import save_remote_voice_config

logging = logger(__name__)


class RemoteVoiceController:
    """Handle remote voice settings, secrets, and Eigi public API calls."""

    def get_settings(self) -> dict[str, Any]:
        """Return current remote voice settings for the dashboard.

        Returns:
            dict[str, Any]: Public remote voice configuration for the UI.
        """
        logging.info("RemoteVoiceController.get_settings")
        return public_remote_voice_config()

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Persist remote voice settings.

        Args:
            updates: Partial settings from the dashboard request.

        Returns:
            dict[str, Any]: Current settings after persistence.
        """
        logging.info("RemoteVoiceController.update_settings")
        if updates.get("public_api_base_url") and not updates.get("daily_session_url"):
            updates["daily_session_url"] = self._daily_url(updates["public_api_base_url"])
        save_remote_voice_config(updates)
        return public_remote_voice_config()

    def get_api_keys(self) -> dict[str, dict[str, str | bool]]:
        """Return masked dashboard-managed API key status.

        Returns:
            dict[str, dict[str, str | bool]]: Per-key configured state and preview.
        """
        logging.info("RemoteVoiceController.get_api_keys")
        return public_secret_status()

    def update_api_keys(self, updates: dict[str, str | None]) -> dict[str, dict[str, str | bool]]:
        """Persist non-empty API key updates to `.env`.

        Args:
            updates: Partial secret updates from the dashboard.

        Returns:
            dict[str, dict[str, str | bool]]: Masked secret status after persistence.
        """
        logging.info("RemoteVoiceController.update_api_keys")
        cleaned = {
            key: value.strip()
            for key, value in updates.items()
            if value is not None and value.strip()
        }
        if cleaned:
            write_env_values(cleaned)
        return public_secret_status()

    def list_agents(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List Eigi agents visible to the configured public API key.

        Args:
            page: Page number for the public API request.
            page_size: Number of results requested from the API.
            search: Optional search query.

        Returns:
            dict[str, Any]: Raw JSON object returned by the Eigi public API.
        """
        logging.info("RemoteVoiceController.list_agents page=%s page_size=%s", page, page_size)
        settings = public_remote_voice_config()
        base_url = settings.get("public_api_base_url") or self._base_url(
            settings.get("daily_session_url", "")
        )
        query = {"page": str(page), "page_size": str(page_size)}
        if search:
            query["search"] = search
        return self._eigi_request(f"{base_url.rstrip('/')}/agents?{urllib.parse.urlencode(query)}")

    def get_agent_dynamic_variables(self, agent_id: str) -> dict[str, Any]:
        """Return dynamic variable definitions for one Eigi agent.

        Args:
            agent_id: Eigi agent identifier.

        Returns:
            dict[str, Any]: Raw JSON object returned by the Eigi public API.
        """
        logging.info("RemoteVoiceController.get_agent_dynamic_variables agent_id=%s", agent_id)
        settings = public_remote_voice_config()
        base_url = settings.get("public_api_base_url") or self._base_url(
            settings.get("daily_session_url", "")
        )
        return self._eigi_request(f"{base_url.rstrip('/')}/agents/{agent_id}/dynamic-variables")

    def _eigi_request(self, url: str) -> dict[str, Any]:
        """Call an Eigi public API endpoint using the configured API key.

        Args:
            url: Fully qualified Eigi public API URL.

        Returns:
            dict[str, Any]: Parsed JSON object from the API response.

        Raises:
            HTTPException: Raised for missing API key, upstream HTTP errors,
                invalid JSON, or unexpected response shapes.
        """
        api_key = read_secret("EIGI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="EIGI_API_KEY is not configured.")

        request = urllib.request.Request(url, headers={"X-API-Key": api_key})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8")
                payload = json.loads(body)
                if not isinstance(payload, dict):
                    raise HTTPException(
                        status_code=502,
                        detail="Eigi API returned a non-object JSON response.",
                    )
                return payload
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logging.error("Eigi API request failed url=%s status=%s", url, exc.code)
            raise HTTPException(status_code=exc.code, detail=detail) from exc
        except urllib.error.URLError as exc:
            logging.error("Eigi API request failed url=%s error=%s", url, exc)
            raise HTTPException(status_code=502, detail=f"Eigi API request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            logging.error("Eigi API returned invalid JSON url=%s", url)
            raise HTTPException(status_code=502, detail="Eigi API returned invalid JSON.") from exc

    @staticmethod
    def _base_url(daily_session_url: str) -> str:
        """Infer the public API base URL from a `/daily` URL."""
        if daily_session_url.endswith("/daily"):
            return daily_session_url[: -len("/daily")]
        return daily_session_url

    @staticmethod
    def _daily_url(public_api_base_url: str) -> str:
        """Build the Daily session URL from an Eigi public API base URL."""
        return f"{public_api_base_url.rstrip('/')}/daily"
