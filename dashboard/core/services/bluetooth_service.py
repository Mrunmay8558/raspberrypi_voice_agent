"""Bluetooth service functions for the dashboard.

This module wraps `bluetoothctl` commands used by the dashboard and converts
their textual output into structured response models for the controller layer.
"""

import re

from dashboard.core.apis.schemas.responses.bluetooth_response import BluetoothDevice
from dashboard.core.services.command_service import run_command

DEVICE_RE = re.compile(r"^Device\s+(?P<mac>[0-9A-Fa-f:]{17})\s+(?P<name>.+)$")


def list_devices() -> list[BluetoothDevice]:
    """Return Bluetooth devices known to `bluetoothctl`.

    Returns:
        list[BluetoothDevice]: Known Bluetooth devices with connection state
        when available.
    """
    output = run_command(["bluetoothctl", "devices"], timeout=10)
    devices = []
    for line in output.splitlines():
        match = DEVICE_RE.match(line.strip())
        if not match:
            continue
        devices.append(_device_from_info(match.group("mac"), match.group("name")))
    return devices


def scan_devices(seconds: int = 8) -> list[BluetoothDevice]:
    """Scan for Bluetooth devices and return the known-device list.

    Args:
        seconds: Duration of the scan window passed to `bluetoothctl`.

    Returns:
        list[BluetoothDevice]: Devices visible after the scan completes.
    """
    try:
        run_command(["timeout", str(seconds), "bluetoothctl", "scan", "on"], timeout=seconds + 2)
    except Exception:
        pass
    return list_devices()


def connect_device(mac: str, pair: bool = True, trust: bool = True) -> str:
    """Pair, trust, and connect a Bluetooth device.

    Args:
        mac: Bluetooth MAC address.
        pair: Whether the device should be paired before connecting.
        trust: Whether the device should be trusted before connecting.

    Returns:
        str: Combined command output from the executed Bluetooth actions.
    """
    output_parts = []
    if pair:
        output_parts.append(run_command(["bluetoothctl", "pair", mac], timeout=30))
    if trust:
        output_parts.append(run_command(["bluetoothctl", "trust", mac], timeout=10))
    output_parts.append(run_command(["bluetoothctl", "connect", mac], timeout=20))
    return "\n".join(part for part in output_parts if part)


def disconnect_device(mac: str) -> str:
    """Disconnect a Bluetooth device by MAC address.

    Args:
        mac: Bluetooth MAC address.

    Returns:
        str: Output from the disconnect command.
    """
    return run_command(["bluetoothctl", "disconnect", mac], timeout=15)


def _device_from_info(mac: str, fallback_name: str) -> BluetoothDevice:
    """Load detailed device metadata from `bluetoothctl info`.

    Args:
        mac: Bluetooth MAC address.
        fallback_name: Device name returned by `bluetoothctl devices`.

    Returns:
        BluetoothDevice: Structured device information.
    """
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
    """Extract a single `bluetoothctl info` field from command output."""
    prefix = f"{key}:"
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return None


def _extract_bool(output: str, key: str) -> bool:
    """Interpret a `bluetoothctl info` field as a boolean flag."""
    return (_extract_value(output, key) or "").lower() == "yes"
