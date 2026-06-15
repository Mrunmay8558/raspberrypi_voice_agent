import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

from config import PROJECT_ROOT
from config import VOICE_CLIENT_BROWSER_BIN
from config import VOICE_CLIENT_BROWSER_HEADLESS
from config import VOICE_CLIENT_HOST
from config import VOICE_CLIENT_PORT
from dashboard.commons.logger import configure_logger
from voice_client.config_store import load_remote_voice_config


def find_browser() -> str:
    if VOICE_CLIENT_BROWSER_BIN:
        return VOICE_CLIENT_BROWSER_BIN

    candidates = [
        "chromium-browser",
        "chromium",
        "google-chrome",
        "google-chrome-stable",
    ]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError(
        "No Chromium browser found. Install chromium-browser or set VOICE_CLIENT_BROWSER_BIN."
    )


def ensure_web_build() -> None:
    index_file = PROJECT_ROOT / "voice_client" / "web" / "dist" / "index.html"
    if not index_file.exists():
        raise RuntimeError(
            "Remote voice client web build is missing. Run: cd voice_client/web && npm install && npm run build"
        )


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def start_browser(url: str) -> subprocess.Popen[bytes]:
    browser = find_browser()
    profile_dir = PROJECT_ROOT / "run" / "voice-client-chromium"
    profile_dir.mkdir(parents=True, exist_ok=True)

    command = [
        browser,
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--disable-session-crashed-bubble",
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-ui-for-media-stream",
        "--disable-features=TranslateUI",
        f"--app={url}",
    ]
    if VOICE_CLIENT_BROWSER_HEADLESS:
        command.insert(1, "--headless=new")

    logger.info("Launching remote voice browser: {}", " ".join(command))
    return subprocess.Popen(command, cwd=PROJECT_ROOT)


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
    if config.client_type not in {"native", "browser"}:
        raise RuntimeError("Remote voice client type must be either 'native' or 'browser'.")
    if config.client_type == "browser":
        ensure_web_build()

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
        if config.client_type == "native":
            client_process = start_native_client(
                broker_url,
                config.native_bin,
                config.native_config_file,
            )
        else:
            client_process = start_browser(f"http://{VOICE_CLIENT_HOST}:{VOICE_CLIENT_PORT}")
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
