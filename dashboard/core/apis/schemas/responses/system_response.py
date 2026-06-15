"""System status response schemas."""

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    """Systemd service status returned by the dashboard."""

    name: str
    active: bool
    sub_state: str


class SystemStatus(BaseModel):
    """Dashboard host and service status."""

    hostname: str
    local_url: str
    services: list[ServiceStatus]
