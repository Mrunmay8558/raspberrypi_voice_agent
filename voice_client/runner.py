"""Run the native Daily audio client behind a local session broker.

The native C++ client expects a Daily-compatible `/start` endpoint. This runner
starts a local FastAPI broker, launches the native binary, and keeps both
processes tied to the wake-listener session lifecycle.
"""

import signal
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

from config import PROJECT_ROOT
from config import VOICE_CLIENT_HOST
from config import VOICE_CLIENT_PORT
from dashboard.commons.logger import configure_logger
from voice_client.config_store import load_remote_voice_config


def resolve_project_path(path_value: str) -> Path:
    """Resolve an absolute or project-relative path."""
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def start_native_client(url: str, native_bin: str, config_file: str) -> subprocess.Popen[bytes]:
    """Launch the native Pipecat Daily client.

    Args:
        url: Local broker URL passed to the native client's `-b` option.
        native_bin: Absolute or project-relative native client executable path.
        config_file: Absolute or project-relative native client JSON config path.

    Returns:
        The running native client process.

    Raises:
        RuntimeError: If the executable or config file does not exist.
    """
    binary = resolve_project_path(native_bin)
    config = resolve_project_path(config_file)
    if not binary.exists():
        raise RuntimeError(
            f"Native Pipecat Daily client not found at {binary}. "
            "Build it with voice_client/native_daily/scripts/build_native_daily_client.sh."
        )
    if not config.exists():
        raise RuntimeError(f"Native Pipecat Daily config file not found at {config}.")

    command = [str(binary), "-b", url, "-c", str(config)]
    logger.info("Launching native remote voice client: {}", " ".join(command))
    return subprocess.Popen(command, cwd=PROJECT_ROOT)


def run_server() -> subprocess.Popen[bytes]:
    """Start the local FastAPI broker used by the native client."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "voice_client.server:app",
        "--host",
        VOICE_CLIENT_HOST,
        "--port",
        str(VOICE_CLIENT_PORT),
    ]
    logger.info("Starting remote voice client broker: {}", " ".join(command))
    return subprocess.Popen(command, cwd=PROJECT_ROOT, start_new_session=True)


def main() -> None:
    """Run the broker and native client until either exits or receives a signal."""
    configure_logger()
    config = load_remote_voice_config()
    if not config.daily_session_url or not config.api_key or not config.agent_id:
        raise RuntimeError(
            "Remote voice client requires daily_session_url and agent_id in user.json, plus EIGI_API_KEY in .env."
        )

    server = run_server()
    client_process: subprocess.Popen[bytes] | None = None
    stopped = False

    def request_stop(signum, _frame):
        nonlocal stopped
        stopped = True
        logger.info("Received signal {}. Stopping remote voice client.", signum)

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    try:
        time.sleep(2)
        broker_url = f"http://{VOICE_CLIENT_HOST}:{VOICE_CLIENT_PORT}/api/start"
        client_process = start_native_client(
            broker_url,
            config.native_bin,
            config.native_config_file,
        )
        while not stopped:
            if server.poll() is not None:
                raise RuntimeError(f"Remote voice client broker exited: {server.returncode}")
            if client_process.poll() is not None:
                logger.info(
                    "Remote voice client exited with code {}",
                    client_process.returncode,
                )
                return
            time.sleep(1)
    finally:
        _stop_process(client_process, "native remote voice client")
        _stop_process(server, "remote voice client broker")


def _stop_process(process: subprocess.Popen[bytes] | None, label: str) -> None:
    """Terminate a subprocess and kill it if graceful shutdown times out."""
    if process is None or process.poll() is not None:
        return

    logger.info("Stopping {}", label)
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        logger.warning("{} did not stop in time; killing it", label)
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()
