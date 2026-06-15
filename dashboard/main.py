"""Primary entrypoint for the dashboard FastAPI application.

This module exposes `app` for ASGI servers and `main()` for direct process
execution via `python -m dashboard.main`.
"""

import uvicorn

from config import DASHBOARD_HOST
from config import DASHBOARD_PORT
from dashboard.core.apis.api import app


def main() -> None:
    """Run the dashboard FastAPI application with Uvicorn."""
    uvicorn.run(
        "dashboard.main:app",
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
