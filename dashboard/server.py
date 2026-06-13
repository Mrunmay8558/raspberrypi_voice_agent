import uvicorn

from config import DASHBOARD_HOST
from config import DASHBOARD_PORT


def main() -> None:
    uvicorn.run(
        "dashboard.main:app",
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
