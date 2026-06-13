import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parent


DEFAULT_HERMES_GATEWAY_COMMAND = "hermes gateway run --replace"
DEFAULT_HERMES_HOST = "127.0.0.1"
DEFAULT_HERMES_PORT = 8642
LOCAL_OPENAI_BASE_URL = f"http://{DEFAULT_HERMES_HOST}:{DEFAULT_HERMES_PORT}/v1"
CLOUDFLARE_OPENAI_BASE_URL = "https://tea-referral-multiple-mtv.trycloudflare.com/v1"
LOCAL_VOICE_TESTING_VALUE = os.getenv("LOCAL_VOICE_TESTING", "true").strip().lower()
if LOCAL_VOICE_TESTING_VALUE not in {"true", "false"}:
    raise ValueError("LOCAL_VOICE_TESTING must be either 'true' or 'false'.")
LOCAL_VOICE_TESTING = LOCAL_VOICE_TESTING_VALUE == "true"
OPENAI_BASE_URL = (
    LOCAL_OPENAI_BASE_URL if LOCAL_VOICE_TESTING else CLOUDFLARE_OPENAI_BASE_URL
)
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "hermes-model")
CARTESIA_VOICE_ID = "71a7ad14-091c-4e8e-a314-022ece01c121"

DEFAULT_CLOUDFLARED_BIN = "cloudflared"
DEFAULT_CLOUDFLARED_WAIT_TIMEOUT_SECS = 90
DEFAULT_CLOUDFLARED_QUICK_TUNNEL = "true"
DEFAULT_CLOUDFLARED_TARGET_URL = f"http://localhost:{DEFAULT_HERMES_PORT}"

DEFAULT_PID_FILE = PROJECT_ROOT / "run" / "bot.pid"
DEFAULT_WAKEWORD_MODEL = os.getenv("WAKEWORD_MODEL", "hey jarvis")
DEFAULT_THRESHOLD = float(os.getenv("WAKEWORD_THRESHOLD", "0.5"))
DEFAULT_COOLDOWN_SECS = float(os.getenv("WAKEWORD_COOLDOWN_SECS", "8.0"))
DEFAULT_VAD_THRESHOLD = float(os.getenv("WAKEWORD_VAD_THRESHOLD", "0.5"))
DEFAULT_INFERENCE_FRAMEWORK = os.getenv("WAKEWORD_INFERENCE_FRAMEWORK", "onnx")

SAMPLE_RATE = 16000
CHUNK_SIZE = 1280

DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8080"))
DASHBOARD_DEBUG = os.getenv("DASHBOARD_DEBUG", "false").strip().lower() == "true"
DASHBOARD_DEFAULT_USERNAME = os.getenv("DASHBOARD_DEFAULT_USERNAME", "admin")
DASHBOARD_SESSION_TTL_HOURS = int(os.getenv("DASHBOARD_SESSION_TTL_HOURS", "12"))
DASHBOARD_AUTH_FILE = Path(
    os.getenv("DASHBOARD_AUTH_FILE", str(PROJECT_ROOT / "run" / "dashboard_auth.json"))
)
DASHBOARD_STATIC_DIR = PROJECT_ROOT / "dashboard" / "static"
