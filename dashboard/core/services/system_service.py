"""System status and systemd helpers for the dashboard.

This module inspects the local host and selected systemd units so the
dashboard can present device health and service state to the user. It also
contains small helpers for controlled service restarts used by other
dashboard features.
"""

import socket

from config import DASHBOARD_PORT
from dashboard.core import logger
from dashboard.core.apis.schemas.responses.system_response import ServiceStatus
from dashboard.core.apis.schemas.responses.system_response import SystemStatus
from dashboard.core.services.command_service import CommandError
from dashboard.core.services.command_service import run_command

logging = logger(__name__)

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


def restart_service(name: str) -> tuple[bool, str]:
    """Restart one systemd unit and report whether it succeeded.

    The dashboard normally runs as a non-root user. On Raspberry Pi images
    where `sudo -n` is allowed for service control, the restart can complete
    directly. Otherwise the save should still succeed and the UI can tell the
    user that a manual restart is required.

    Args:
        name: Systemd unit to restart.

    Returns:
        tuple[bool, str]: Success flag and a short status message.
    """
    commands = (
        ["sudo", "-n", "systemctl", "restart", name],
        ["systemctl", "restart", name],
    )
    last_error = "Restart was not attempted."
    for command in commands:
        try:
            run_command(command, timeout=20)
            logging.info("Restarted service name=%s command=%s", name, " ".join(command))
            return True, f"Restarted {name}."
        except CommandError as exc:
            last_error = exc.output or f"Failed to restart {name}."
            logging.warning(
                "Failed to restart service name=%s command=%s output=%s",
                name,
                " ".join(command),
                last_error,
            )
    return False, f"Saved settings, but could not restart {name}: {last_error}"


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
