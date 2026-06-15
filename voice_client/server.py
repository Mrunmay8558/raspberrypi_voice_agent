"""Expose a local broker API for the native Pipecat Daily client.

The native C++ client connects to this small FastAPI app rather than calling
the Eigi Daily endpoint directly. The broker normalizes session creation and
accepts client event callbacks for local logging.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi import HTTPException
from loguru import logger

from dashboard.commons.logger import configure_logger
from voice_client.config_store import load_remote_voice_config
from voice_client.session import RemoteSessionError
from voice_client.session import create_daily_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure broker logging around the FastAPI application lifecycle.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control returns to FastAPI after startup completes.
    """
    configure_logger()
    logger.info("Remote voice client broker starting")
    yield
    logger.info("Remote voice client broker stopping")


app = FastAPI(
    title="Remote Pipecat Voice Client",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/")
def index():
    """Return a simple health payload for the local broker.

    Returns:
        dict[str, str]: Minimal status response for health checks.
    """
    return {"status": "ok", "client": "native_daily"}


@app.post("/api/start")
def start():
    """Create one Daily session for the native client startup flow.

    Returns:
        dict[str, Any]: Normalized Eigi Daily session payload.

    Raises:
        HTTPException: Raised when the upstream session request fails.
    """
    try:
        session = create_daily_session(load_remote_voice_config())
    except RemoteSessionError as exc:
        logger.error("Failed to create remote Daily session: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return session


@app.post("/api/events")
def events(payload: dict[str, Any]):
    """Receive fire-and-forget runtime events from the native client.

    Args:
        payload: Event payload emitted by the native client.

    Returns:
        dict[str, bool]: Static acknowledgement response.
    """
    event = payload.get("event", "unknown")
    data = payload.get("data")
    logger.info("Pipecat client event={} data={}", event, data)
    return {"ok": True}
