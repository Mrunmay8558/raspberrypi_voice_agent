from pydantic import BaseModel


class ServiceStatus(BaseModel):
    name: str
    active: bool
    sub_state: str


class SystemStatus(BaseModel):
    hostname: str
    local_url: str
    services: list[ServiceStatus]
