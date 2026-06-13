import csv
from io import StringIO

from dashboard.schemas.wifi import WifiNetwork
from dashboard.services.command_service import run_command


def scan_networks() -> list[WifiNetwork]:
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
    return run_command(
        ["nmcli", "device", "wifi", "connect", ssid, "password", password],
        timeout=45,
    )
