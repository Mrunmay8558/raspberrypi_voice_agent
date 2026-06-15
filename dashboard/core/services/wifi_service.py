"""WiFi service functions for the dashboard.

This module wraps NetworkManager commands used by the dashboard and converts
their textual output into structured response models for the controller layer.
"""

import csv
from io import StringIO

from dashboard.core.apis.schemas.responses.wifi_response import WifiNetwork
from dashboard.core.services.command_service import run_command


def scan_networks() -> list[WifiNetwork]:
    """Scan nearby WiFi networks using NetworkManager.

    Returns:
        list[WifiNetwork]: Visible WiFi networks ordered by signal strength.
    """
    output = run_command(
        [
            "nmcli",
            "--terse",
            "--escape",
            "yes",
            "--fields",
            "IN-USE,SSID,SIGNAL,SECURITY",
            "device",
            "wifi",
            "list",
            "--rescan",
            "yes",
        ],
        timeout=30,
    )
    networks: dict[str, WifiNetwork] = {}
    for row in csv.reader(StringIO(output), delimiter=":"):
        if len(row) < 4:
            continue
        active, ssid, signal, security = row[:4]
        if not ssid:
            continue
        existing = networks.get(ssid)
        parsed = WifiNetwork(
            ssid=ssid,
            signal=int(signal) if signal.isdigit() else None,
            security=security or None,
            active=active == "*",
        )
        if existing is None or (parsed.signal or 0) > (existing.signal or 0):
            networks[ssid] = parsed
    return sorted(networks.values(), key=lambda item: item.signal or 0, reverse=True)


def connect_network(ssid: str, password: str) -> str:
    """Connect to a WiFi network using NetworkManager.

    Args:
        ssid: WiFi network name.
        password: WiFi password.

    Returns:
        str: Output from the NetworkManager connection command.
    """
    return run_command(
        ["nmcli", "device", "wifi", "connect", ssid, "password", password],
        timeout=45,
    )
