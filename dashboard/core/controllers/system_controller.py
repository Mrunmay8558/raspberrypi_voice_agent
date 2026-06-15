"""Business logic layer for dashboard system status.

This controller coordinates dashboard-facing host status requests and keeps
the route layer free of service implementation details.
"""

from dashboard.core import logger
from dashboard.core.services.system_service import get_status

logging = logger(__name__)


class SystemController:
    """Coordinate dashboard host and service status retrieval."""

    def get_status(self):
        """Return current dashboard system status.

        Returns:
            SystemStatus: Hostname, local dashboard URL, and service states.
        """
        logging.info("SystemController.get_status")
        return get_status()
