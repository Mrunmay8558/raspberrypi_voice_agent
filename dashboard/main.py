from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import DASHBOARD_DEBUG
from config import DASHBOARD_STATIC_DIR
from dashboard.commons.logger import configure_logger
from dashboard.core.security import AuthStore
from dashboard.routers import auth
from dashboard.routers import bluetooth
from dashboard.routers import system
from dashboard.routers import wifi


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logger(DASHBOARD_DEBUG)
    auth_store = AuthStore()
    app.state.auth_store = auth_store
    generated = auth_store.ensure_credentials()
    if generated:
        logger.warning(
            "First dashboard login is username='{}' password='{}'",
            generated.username,
            generated.password,
        )
    logger.info("Dashboard starting")
    yield
    logger.info("Dashboard stopping")


app = FastAPI(
    title="Raspberry Pi Voice Agent Dashboard",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(system.router)
app.include_router(wifi.router)
app.include_router(bluetooth.router)
app.mount("/static", StaticFiles(directory=DASHBOARD_STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(DASHBOARD_STATIC_DIR / "index.html")
