import socket

from config import DASHBOARD_HOST
from config import DASHBOARD_PORT
from dashboard.schemas.system import ServiceStatus
from dashboard.schemas.system import SystemStatus
from dashboard.services.command_service import CommandError
from dashboard.services.command_service import run_command

SERVICES = [
    "voice-assistant-stack.target",
    "dashboard.service",
    "hermes-gateway.service",
    "cloudflared-hermes-tunnel.service",
    "voice-bot-wake.service",
]


def get_status() -> SystemStatus:
    hostname = socket.gethostname()
    return SystemStatus(
        hostname=hostname,
        local_url=f"http://{hostname}.local:{DASHBOARD_PORT}",
        services=[_service_status(name) for name in SERVICES],
    )


def _service_status(name: str) -> ServiceStatus:
    try:
        active_state = run_command(
            ["systemctl", "show", name, "--property=ActiveState", "--value"], timeout=5
        ).strip()
        sub_state = run_command(
            ["systemctl", "show", name, "--property=SubState", "--value"], timeout=5
        ).strip()
    except CommandError as exc:
        active_state = "unknown"
        sub_state = exc.output or "unavailable"

    return ServiceStatus(
        name=name,
        active=active_state == "active",
        sub_state=sub_state,
    )
