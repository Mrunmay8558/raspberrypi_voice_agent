"""FastAPI application bootstrap for the dashboard."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import DASHBOARD_DEBUG
from config import DASHBOARD_STATIC_DIR
from dashboard.commons.auth import AuthStore
from dashboard.commons.logger import configure_logger
from dashboard.core import logger
from dashboard.core.apis.routes.auth_router import auth_router
from dashboard.core.apis.routes.bluetooth_router import bluetooth_router
from dashboard.core.apis.routes.remote_voice_router import remote_voice_router
from dashboard.core.apis.routes.system_router import system_router
from dashboard.core.apis.routes.wifi_router import wifi_router

logging = logger(__name__)
API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize dashboard-wide runtime state.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control returns to FastAPI after startup has completed.
    """
    configure_logger(DASHBOARD_DEBUG)
    auth_store = AuthStore()
    app.state.auth_store = auth_store

    generated = auth_store.ensure_credentials()
    if generated:
        logging.warning(
            "First dashboard login is username='%s' password='%s'",
            generated.username,
            generated.password,
        )

    logging.info("Dashboard starting")
    yield
    logging.info("Dashboard stopping")


app = FastAPI(
    title="Raspberry Pi Voice Agent Dashboard",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Attach baseline browser security headers to dashboard responses.

    Args:
        request: Incoming HTTP request.
        call_next: Next ASGI handler in the middleware stack.

    Returns:
        Response: Downstream response with dashboard security headers.
    """
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = "geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(system_router, prefix=API_V1_PREFIX)
app.include_router(wifi_router, prefix=API_V1_PREFIX)
app.include_router(bluetooth_router, prefix=API_V1_PREFIX)
app.include_router(remote_voice_router, prefix=API_V1_PREFIX)
app.mount("/static", StaticFiles(directory=DASHBOARD_STATIC_DIR), name="static")


@app.get("/")
def index():
    """Serve the dashboard frontend shell.

    Returns:
        FileResponse: Dashboard HTML entrypoint.
    """
    return FileResponse(DASHBOARD_STATIC_DIR / "index.html")
