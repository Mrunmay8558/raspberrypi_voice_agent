"""System status service functions for the dashboard.

This module inspects the local host and selected systemd units so the
dashboard can present device health and service state to the user.
"""

import socket

from config import DASHBOARD_PORT
from dashboard.core.apis.schemas.responses.system_response import ServiceStatus
from dashboard.core.apis.schemas.responses.system_response import SystemStatus
from dashboard.core.services.command_service import CommandError
from dashboard.core.services.command_service import run_command

SERVICES = [
    "voice-assistant-stack.target",
    "dashboard.service",
    "hermes-gateway.service",
    "cloudflared-hermes-tunnel.service",
    "voice-bot-wake.service",
]


def get_status() -> SystemStatus:
    """Return host and systemd service status for the dashboard.

    Returns:
        SystemStatus: Hostname, local dashboard URL, and selected service
        states.
    """
    hostname = socket.gethostname()
    return SystemStatus(
        hostname=hostname,
        local_url=f"http://{hostname}.local:{DASHBOARD_PORT}",
        services=[_service_status(name) for name in SERVICES],
    )


def _service_status(name: str) -> ServiceStatus:
    """Return the active/sub-state for one systemd unit.

    Args:
        name: Systemd unit name.

    Returns:
        ServiceStatus: Structured service state for the requested unit.
    """
    try:
        active_state = run_command(
            ["systemctl", "show", name, "--property=ActiveState", "--value"],
            timeout=5,
        ).strip()
        sub_state = run_command(
            ["systemctl", "show", name, "--property=SubState", "--value"],
            timeout=5,
        ).strip()
    except CommandError as exc:
        active_state = "unknown"
        sub_state = exc.output or "unavailable"

    return ServiceStatus(
        name=name,
        active=active_state == "active",
        sub_state=sub_state,
    )
