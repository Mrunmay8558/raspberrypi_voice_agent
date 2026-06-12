import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import openwakeword
import sounddevice as sd
from loguru import logger
from openwakeword.model import Model

from config import CHUNK_SIZE
from config import DEFAULT_COOLDOWN_SECS
from config import DEFAULT_INFERENCE_FRAMEWORK
from config import DEFAULT_PID_FILE
from config import DEFAULT_THRESHOLD
from config import DEFAULT_VAD_THRESHOLD
from config import DEFAULT_WAKEWORD_MODEL
from config import PROJECT_ROOT
from config import SAMPLE_RATE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Listen for a wake word and start the Daily bot when detected."
    )
    parser.add_argument(
        "--wakeword-model",
        default=os.getenv("WAKEWORD_MODEL", DEFAULT_WAKEWORD_MODEL),
        help="Pretrained openWakeWord model name or a path to a custom model file.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.getenv("WAKEWORD_THRESHOLD", str(DEFAULT_THRESHOLD))),
        help="Minimum wake-word score required to launch the bot.",
    )
    parser.add_argument(
        "--cooldown-secs",
        type=float,
        default=float(os.getenv("WAKEWORD_COOLDOWN_SECS", str(DEFAULT_COOLDOWN_SECS))),
        help="Minimum time between wake detections.",
    )
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=float(os.getenv("WAKEWORD_VAD_THRESHOLD", str(DEFAULT_VAD_THRESHOLD))),
        help="Silero VAD threshold used to suppress non-speech false positives.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Optional sounddevice input device name or index.",
    )
    parser.add_argument(
        "--inference-framework",
        choices=["tflite", "onnx"],
        default=os.getenv("WAKEWORD_INFERENCE_FRAMEWORK", DEFAULT_INFERENCE_FRAMEWORK),
        help="Inference backend to use for openWakeWord.",
    )
    parser.add_argument(
        "--pid-file",
        default=str(DEFAULT_PID_FILE),
        help="Path used to track the running bot process.",
    )
    parser.add_argument(
        "--transport",
        default="daily",
        help="Transport passed to bot.py via -t. Defaults to daily.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def configure_logging(debug: bool) -> None:
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if debug else "INFO")


def ensure_runtime_path(pid_file: Path) -> None:
    pid_file.parent.mkdir(parents=True, exist_ok=True)


def read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None

    try:
        return int(pid_file.read_text().strip())
    except (OSError, ValueError):
        return None


def clear_stale_pid(pid_file: Path) -> None:
    try:
        pid_file.unlink(missing_ok=True)
    except OSError:
        logger.warning("Failed to remove pid file {}", pid_file)


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def looks_like_bot_process(pid: int) -> bool:
    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    if not proc_cmdline.exists():
        return True

    try:
        cmdline = proc_cmdline.read_text().replace("\x00", " ")
    except OSError:
        return True

    return "voice_bot.bot" in cmdline and "-t" in cmdline


def active_bot_pid(pid_file: Path) -> int | None:
    pid = read_pid(pid_file)
    if pid is None:
        return None
    if process_exists(pid) and looks_like_bot_process(pid):
        return pid
    clear_stale_pid(pid_file)
    return None


def write_pid(pid_file: Path, pid: int) -> None:
    pid_file.write_text(f"{pid}\n")


def start_bot(transport: str, pid_file: Path) -> subprocess.Popen[bytes] | None:
    current_pid = active_bot_pid(pid_file)
    if current_pid is not None:
        logger.info("Bot already running with pid {}", current_pid)
        return None

    command = [sys.executable, "-m", "voice_bot.bot", "-t", transport]
    process = subprocess.Popen(command, cwd=PROJECT_ROOT, start_new_session=True)
    write_pid(pid_file, process.pid)
    logger.info("Started bot process pid={} command={}", process.pid, " ".join(command))
    return process


def reap_bot_process(
    process: subprocess.Popen[bytes] | None, pid_file: Path
) -> subprocess.Popen[bytes] | None:
    if process is None:
        active_bot_pid(pid_file)
        return None
    exit_code = process.poll()
    if exit_code is None:
        return process
    logger.info("Bot process pid={} exited with code {}", process.pid, exit_code)
    clear_stale_pid(pid_file)
    return None


def load_wakeword_model(
    model_name: str, vad_threshold: float, inference_framework: str
) -> tuple[Model, str]:
    openwakeword.utils.download_models()
    model = Model(
        wakeword_models=[model_name],
        vad_threshold=vad_threshold,
        inference_framework=inference_framework,
    )
    loaded_name = next(iter(model.models.keys()))
    return model, loaded_name


def run_listener(args: argparse.Namespace) -> None:
    pid_file = Path(args.pid_file)
    ensure_runtime_path(pid_file)

    model, loaded_name = load_wakeword_model(
        model_name=args.wakeword_model,
        vad_threshold=args.vad_threshold,
        inference_framework=args.inference_framework,
    )

    logger.info(
        "Listening for wake word '{}' using '{}' with threshold {}",
        args.wakeword_model,
        loaded_name,
        args.threshold,
    )

    stop_requested = False
    bot_process: subprocess.Popen[bytes] | None = None
    last_trigger_time = 0.0

    def request_stop(signum, _frame):
        nonlocal stop_requested
        stop_requested = True
        logger.info("Received signal {}. Stopping wake listener.", signum)

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=CHUNK_SIZE,
        dtype="int16",
        channels=1,
        device=args.device,
    ) as stream:
        while not stop_requested:
            bot_process = reap_bot_process(bot_process, pid_file)
            raw_audio, overflowed = stream.read(CHUNK_SIZE)
            if overflowed:
                logger.warning("Wake listener audio input overflowed")

            predictions = model.predict(np.frombuffer(raw_audio, dtype=np.int16))
            score = float(predictions.get(loaded_name, 0.0))

            logger.debug("Wake-word score {}={:.3f}", loaded_name, score)

            now = time.monotonic()
            if score < args.threshold:
                continue
            if now - last_trigger_time < args.cooldown_secs:
                logger.info("Wake word detected but cooldown is still active")
                continue

            logger.info("Wake word '{}' detected with score {:.3f}", loaded_name, score)
            launched_process = start_bot(args.transport, pid_file)
            if launched_process is not None:
                bot_process = launched_process
            last_trigger_time = now


def main() -> None:
    args = parse_args()
    configure_logging(args.debug)
    run_listener(args)


if __name__ == "__main__":
    main()