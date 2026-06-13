import re

from dashboard.schemas.bluetooth import BluetoothDevice
from dashboard.services.command_service import run_command


DEVICE_RE = re.compile(r"^Device\s+(?P<mac>[0-9A-Fa-f:]{17})\s+(?P<name>.+)$")


def list_devices() -> list[BluetoothDevice]:
    output = run_command(["bluetoothctl", "devices"], timeout=10)
    devices = []
    for line in output.splitlines():
        match = DEVICE_RE.match(line.strip())
        if not match:
            continue
        devices.append(_device_from_info(match.group("mac"), match.group("name")))
    return devices


def scan_devices(seconds: int = 8) -> list[BluetoothDevice]:
    try:
        run_command(["timeout", str(seconds), "bluetoothctl", "scan", "on"], timeout=seconds + 2)
    except Exception:
        pass
    return list_devices()


def connect_device(mac: str, pair: bool = True, trust: bool = True) -> str:
    output_parts = []
    if pair:
        output_parts.append(run_command(["bluetoothctl", "pair", mac], timeout=30))
    if trust:
        output_parts.append(run_command(["bluetoothctl", "trust", mac], timeout=10))
    output_parts.append(run_command(["bluetoothctl", "connect", mac], timeout=20))
    return "\n".join(part for part in output_parts if part)


def disconnect_device(mac: str) -> str:
    return run_command(["bluetoothctl", "disconnect", mac], timeout=15)


def _device_from_info(mac: str, fallback_name: str) -> BluetoothDevice:
    try:
        output = run_command(["bluetoothctl", "info", mac], timeout=10)
    except Exception:
        return BluetoothDevice(mac=mac, name=fallback_name)

    return BluetoothDevice(
        mac=mac,
        name=_extract_value(output, "Name") or fallback_name,
        connected=_extract_bool(output, "Connected"),
        paired=_extract_bool(output, "Paired"),
        trusted=_extract_bool(output, "Trusted"),
    )


def _extract_value(output: str, key: str) -> str | None:
    prefix = f"{key}:"
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return None


def _extract_bool(output: str, key: str) -> bool:
    return (_extract_value(output, key) or "").lower() == "yes"
