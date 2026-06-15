"""Command-line dashboard for devices without a browser.

This module exposes the same operational surface as the local FastAPI
dashboard, but calls the dashboard controllers directly so it can run on
headless devices without a web browser or HTTP server.
"""

import argparse
import getpass
import json
import sys
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from dashboard.commons.logger import configure_logger
from dashboard.core.controllers.bluetooth_controller import BluetoothController
from dashboard.core.controllers.remote_voice_controller import RemoteVoiceController
from dashboard.core.controllers.system_controller import SystemController
from dashboard.core.controllers.wifi_controller import WifiController


def parse_args() -> argparse.Namespace:
    """Parse dashboard CLI arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m dashboard.cli",
        description="Manage Raspberry Pi voice-agent setup without a browser.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print command output as JSON instead of a readable summary.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_status_parser(subparsers)
    _add_wifi_parser(subparsers)
    _add_bluetooth_parser(subparsers)
    _add_remote_voice_parser(subparsers)
    _add_api_key_parser(subparsers)
    return parser.parse_args()


def _add_status_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the service-status command."""
    subparsers.add_parser("status", help="Show dashboard and voice service status.")


def _add_wifi_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register WiFi management commands."""
    wifi_parser = subparsers.add_parser("wifi", help="Manage WiFi networks.")
    wifi_subparsers = wifi_parser.add_subparsers(dest="wifi_command", required=True)

    wifi_subparsers.add_parser("scan", help="Scan nearby WiFi networks.")

    connect_parser = wifi_subparsers.add_parser("connect", help="Connect to a WiFi network.")
    connect_parser.add_argument("ssid", help="WiFi network name.")
    connect_parser.add_argument(
        "--password",
        help="WiFi password. If omitted, the CLI prompts without echo.",
    )


def _add_bluetooth_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register Bluetooth management commands."""
    bluetooth_parser = subparsers.add_parser("bluetooth", help="Manage Bluetooth devices.")
    bluetooth_subparsers = bluetooth_parser.add_subparsers(
        dest="bluetooth_command",
        required=True,
    )

    bluetooth_subparsers.add_parser("devices", help="List known Bluetooth devices.")
    bluetooth_subparsers.add_parser("scan", help="Scan for Bluetooth devices.")

    connect_parser = bluetooth_subparsers.add_parser(
        "connect",
        help="Pair, trust, and connect a Bluetooth device.",
    )
    connect_parser.add_argument("mac", help="Bluetooth MAC address.")
    connect_parser.add_argument("--no-pair", action="store_true", help="Skip pairing.")
    connect_parser.add_argument("--no-trust", action="store_true", help="Skip trust setup.")

    disconnect_parser = bluetooth_subparsers.add_parser(
        "disconnect",
        help="Disconnect a Bluetooth device.",
    )
    disconnect_parser.add_argument("mac", help="Bluetooth MAC address.")


def _add_remote_voice_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register remote voice configuration commands."""
    remote_parser = subparsers.add_parser(
        "remote-voice",
        help="Manage remote Daily voice settings.",
    )
    remote_subparsers = remote_parser.add_subparsers(
        dest="remote_voice_command",
        required=True,
    )

    remote_subparsers.add_parser("show", help="Show current remote voice settings.")

    set_parser = remote_subparsers.add_parser("set", help="Update remote voice settings.")
    set_parser.add_argument("--runtime-mode", choices=["local", "remote_daily"])
    set_parser.add_argument("--public-api-base-url")
    set_parser.add_argument("--daily-session-url")
    set_parser.add_argument("--agent-id")
    set_parser.add_argument("--conversation-config-type")
    set_parser.add_argument("--conversation-visibility", choices=["true", "false"])
    set_parser.add_argument("--is-test-call", choices=["true", "false"])
    set_parser.add_argument("--native-bin")
    set_parser.add_argument("--native-config-file")
    set_parser.add_argument(
        "--conversation-metadata-json",
        help="JSON object stored as conversation_metadata.",
    )
    set_parser.add_argument(
        "--dynamic-variables-json",
        help="JSON object stored as dynamic_variables.",
    )

    remote_subparsers.add_parser("agents", help="List agents from the Eigi public API.")


def _add_api_key_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register dashboard-managed API key commands."""
    api_parser = subparsers.add_parser("api-keys", help="Manage API keys in .env.")
    api_subparsers = api_parser.add_subparsers(dest="api_key_command", required=True)

    api_subparsers.add_parser("show", help="Show masked API key status.")

    set_parser = api_subparsers.add_parser("set", help="Set one or more API keys.")
    set_parser.add_argument("--eigi")
    set_parser.add_argument("--openai")
    set_parser.add_argument("--deepgram")
    set_parser.add_argument("--cartesia")


def main() -> None:
    """Run the no-browser dashboard CLI."""
    configure_logger()
    args = parse_args()
    try:
        result = dispatch(args)
    except HTTPException as exc:
        print(f"error: {exc.detail}", file=sys.stderr)
        raise SystemExit(1) from exc
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print_result(result, as_json=args.json)


def dispatch(args: argparse.Namespace) -> Any:
    """Execute the selected CLI command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Any: Controller result or a printable data structure.
    """
    if args.command == "status":
        return SystemController().get_status()
    if args.command == "wifi":
        return dispatch_wifi(args)
    if args.command == "bluetooth":
        return dispatch_bluetooth(args)
    if args.command == "remote-voice":
        return dispatch_remote_voice(args)
    if args.command == "api-keys":
        return dispatch_api_keys(args)
    raise ValueError(f"Unsupported command: {args.command}")


def dispatch_wifi(args: argparse.Namespace) -> Any:
    """Execute a WiFi CLI command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Any: WiFi controller result.
    """
    controller = WifiController()
    if args.wifi_command == "scan":
        return controller.scan_networks()
    if args.wifi_command == "connect":
        password = args.password or getpass.getpass("WiFi password: ")
        return controller.connect_network(args.ssid, password)
    raise ValueError(f"Unsupported WiFi command: {args.wifi_command}")


def dispatch_bluetooth(args: argparse.Namespace) -> Any:
    """Execute a Bluetooth CLI command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Any: Bluetooth controller result.
    """
    controller = BluetoothController()
    if args.bluetooth_command == "devices":
        return controller.list_devices()
    if args.bluetooth_command == "scan":
        return controller.scan_devices()
    if args.bluetooth_command == "connect":
        return controller.connect_device(
            args.mac,
            pair=not args.no_pair,
            trust=not args.no_trust,
        )
    if args.bluetooth_command == "disconnect":
        return controller.disconnect_device(args.mac)
    raise ValueError(f"Unsupported Bluetooth command: {args.bluetooth_command}")


def dispatch_remote_voice(args: argparse.Namespace) -> Any:
    """Execute a remote voice CLI command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Any: Remote voice controller result.
    """
    controller = RemoteVoiceController()
    if args.remote_voice_command == "show":
        return controller.get_settings()
    if args.remote_voice_command == "agents":
        return controller.list_agents()
    if args.remote_voice_command == "set":
        updates = _remote_voice_updates(args)
        if not updates:
            raise ValueError("No remote voice settings were provided.")
        return controller.update_settings(updates)
    raise ValueError(f"Unsupported remote voice command: {args.remote_voice_command}")


def dispatch_api_keys(args: argparse.Namespace) -> Any:
    """Execute an API-key CLI command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Any: Remote voice controller result.
    """
    controller = RemoteVoiceController()
    if args.api_key_command == "show":
        return controller.get_api_keys()
    if args.api_key_command == "set":
        updates = {
            "EIGI_API_KEY": args.eigi,
            "OPENAI_API_KEY": args.openai,
            "DEEPGRAM_API_KEY": args.deepgram,
            "CARTESIA_API_KEY": args.cartesia,
        }
        updates = {key: value for key, value in updates.items() if value}
        if not updates:
            raise ValueError("No API keys were provided.")
        return controller.update_api_keys(updates)
    raise ValueError(f"Unsupported API key command: {args.api_key_command}")


def _remote_voice_updates(args: argparse.Namespace) -> dict[str, Any]:
    """Build a remote voice update object from CLI arguments.

    Args:
        args: Parsed remote-voice command arguments.

    Returns:
        dict[str, Any]: Partial settings update for `RemoteVoiceController`.
    """
    updates = {
        "runtime_mode": args.runtime_mode,
        "public_api_base_url": args.public_api_base_url,
        "daily_session_url": args.daily_session_url,
        "agent_id": args.agent_id,
        "conversation_config_type": args.conversation_config_type,
        "native_bin": args.native_bin,
        "native_config_file": args.native_config_file,
    }
    if args.conversation_visibility is not None:
        updates["conversation_visibility"] = _parse_bool(args.conversation_visibility)
    if args.is_test_call is not None:
        updates["is_test_call"] = _parse_bool(args.is_test_call)
    if args.conversation_metadata_json:
        updates["conversation_metadata"] = _parse_json_object(
            args.conversation_metadata_json,
            "conversation_metadata",
        )
    if args.dynamic_variables_json:
        updates["dynamic_variables"] = _parse_json_object(
            args.dynamic_variables_json,
            "dynamic_variables",
        )
    return {key: value for key, value in updates.items() if value is not None}


def _parse_bool(value: str) -> bool:
    """Parse a strict CLI boolean string.

    Args:
        value: String value from argparse.

    Returns:
        bool: Parsed boolean value.
    """
    return value.strip().lower() == "true"


def _parse_json_object(value: str, label: str) -> dict[str, Any]:
    """Parse a JSON object from a CLI argument.

    Args:
        value: JSON string supplied by the user.
        label: Human-readable field name for errors.

    Returns:
        dict[str, Any]: Parsed JSON object.

    Raises:
        ValueError: If the value is invalid JSON or not an object.
    """
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return parsed


def print_result(result: Any, *, as_json: bool) -> None:
    """Print a CLI result.

    Args:
        result: Controller result to render.
        as_json: Whether to force JSON output.
    """
    data = serialize(result)
    if as_json:
        print(json.dumps(data, indent=2))
        return
    print_readable(data)


def serialize(value: Any) -> Any:
    """Convert Pydantic models and containers into JSON-safe values.

    Args:
        value: Arbitrary controller result.

    Returns:
        Any: JSON-serializable representation.
    """
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value


def print_readable(data: Any) -> None:
    """Print a readable text representation for common CLI results.

    Args:
        data: JSON-safe result data.
    """
    if isinstance(data, list):
        for item in data:
            print(_format_item(item))
        return
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{key}: {json.dumps(value, indent=2)}")
            else:
                print(f"{key}: {value}")
        return
    print(data)


def _format_item(item: Any) -> str:
    """Format one list item for readable CLI output.

    Args:
        item: JSON-safe list item.

    Returns:
        str: Single-line item representation.
    """
    if not isinstance(item, dict):
        return str(item)
    return "  ".join(f"{key}={value}" for key, value in item.items())


if __name__ == "__main__":
    main()
