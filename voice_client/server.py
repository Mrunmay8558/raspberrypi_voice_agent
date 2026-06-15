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
    return {"status": "ok", "client": "native_daily"}


@app.post("/api/start")
def start():
    try:
        session = create_daily_session(load_remote_voice_config())
    except RemoteSessionError as exc:
        logger.error("Failed to create remote Daily session: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return session


@app.post("/api/events")
def events(payload: dict[str, Any]):
    event = payload.get("event", "unknown")
    data = payload.get("data")
    logger.info("Pipecat client event={} data={}", event, data)
    return {"ok": True}

