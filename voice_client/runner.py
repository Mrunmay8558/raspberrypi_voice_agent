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
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def start_native_client(url: str, native_bin: str, config_file: str) -> subprocess.Popen[bytes]:
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
        if client_process and client_process.poll() is None:
            client_process.terminate()
            try:
                client_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                client_process.kill()
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    main()
