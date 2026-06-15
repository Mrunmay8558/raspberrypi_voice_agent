from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import PROJECT_ROOT
from dashboard.commons.logger import configure_logger
from voice_client.config_store import load_remote_voice_config
from voice_client.session import RemoteSessionError
from voice_client.session import create_daily_session

STATIC_DIR = PROJECT_ROOT / "voice_client" / "web" / "dist"


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
    if not (STATIC_DIR / "index.html").exists():
        raise HTTPException(
            status_code=500,
            detail="Remote voice client web build is missing. Run: cd voice_client/web && npm install && npm run build",
        )
    return FileResponse(STATIC_DIR / "index.html")


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


app.mount(
    "/assets",
    StaticFiles(directory=STATIC_DIR / "assets", check_dir=False),
    name="assets",
)
