"""Continuously listen for a wake word and launch the selected runtime mode.

This module keeps the microphone open for wake-word detection, starts either
the local voice bot or the remote Daily client, and prevents duplicate session
launches with a pid file and process checks.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import openwakeword
import resampy
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
from config import VOICE_RUNTIME_MODE


def parse_args() -> argparse.Namespace:
    """Parse wake-listener CLI arguments.

    Returns:
        argparse.Namespace: Parsed command-line options for the listener.
    """
    parser = argparse.ArgumentParser(
        description="Listen for a wake word and start the local voice bot when detected."
    )
    parser.add_argument(
        "--wakeword-model",
        default=DEFAULT_WAKEWORD_MODEL,
        help="Pretrained openWakeWord model name or a path to a custom model file.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Minimum wake-word score required to launch the bot.",
    )
    parser.add_argument(
        "--cooldown-secs",
        type=float,
        default=DEFAULT_COOLDOWN_SECS,
        help="Minimum time between wake detections.",
    )
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=DEFAULT_VAD_THRESHOLD,
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
        default=DEFAULT_INFERENCE_FRAMEWORK,
        help="Inference backend to use for openWakeWord.",
    )
    parser.add_argument(
        "--pid-file",
        default=str(DEFAULT_PID_FILE),
        help="Path used to track the running bot process.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def configure_logging(debug: bool) -> None:
    """Configure loguru output for the wake listener process.

    Args:
        debug: Whether DEBUG-level logging should be enabled.
    """
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if debug else "INFO")


def ensure_runtime_path(pid_file: Path) -> None:
    """Create the parent directory used for pid/runtime files.

    Args:
        pid_file: Pid file path whose parent directory must exist.
    """
    pid_file.parent.mkdir(parents=True, exist_ok=True)


def read_pid(pid_file: Path) -> int | None:
    """Read the tracked runtime pid from disk when present.

    Args:
        pid_file: Pid file used for runtime process tracking.

    Returns:
        int | None: Parsed pid, or `None` when unavailable or invalid.
    """
    if not pid_file.exists():
        return None

    try:
        return int(pid_file.read_text().strip())
    except (OSError, ValueError):
        return None


def clear_stale_pid(pid_file: Path) -> None:
    """Remove a pid file that no longer points at a live runtime process.

    Args:
        pid_file: Pid file to delete.
    """
    try:
        pid_file.unlink(missing_ok=True)
    except OSError:
        logger.warning("Failed to remove pid file {}", pid_file)


def process_exists(pid: int) -> bool:
    """Return whether a process id currently exists.

    Args:
        pid: Process id to probe.

    Returns:
        bool: `True` when the pid currently exists.
    """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def looks_like_bot_process(pid: int) -> bool:
    """Best-effort check that a pid belongs to the expected voice runtime.

    Args:
        pid: Process id to inspect.

    Returns:
        bool: `True` when the process appears to be the local bot or remote
        voice client.
    """
    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    if not proc_cmdline.exists():
        return True

    try:
        cmdline = proc_cmdline.read_text().replace("\x00", " ")
    except OSError:
        return True

    return "voice_bot.bot" in cmdline or "voice_client.runner" in cmdline


def active_bot_pid(pid_file: Path) -> int | None:
    """Return the active runtime pid, clearing stale pid files when needed.

    Args:
        pid_file: Pid file used for runtime process tracking.

    Returns:
        int | None: Active runtime pid, or `None` when no valid process exists.
    """
    pid = read_pid(pid_file)
    if pid is None:
        return None
    if process_exists(pid) and looks_like_bot_process(pid):
        return pid
    clear_stale_pid(pid_file)
    return None


def write_pid(pid_file: Path, pid: int) -> None:
    """Persist the current runtime pid for duplicate-launch protection.

    Args:
        pid_file: Pid file used for runtime process tracking.
        pid: Runtime process id to persist.
    """
    pid_file.write_text(f"{pid}\n")


def start_bot(pid_file: Path) -> subprocess.Popen[bytes] | None:
    """Start the configured voice runtime unless one is already active.

    Args:
        pid_file: Pid file used for runtime process tracking.

    Returns:
        subprocess.Popen[bytes] | None: Newly started runtime process, or
        `None` when another session is already active.
    """
    current_pid = active_bot_pid(pid_file)
    if current_pid is not None:
        logger.info("Bot already running with pid {}", current_pid)
        return None

    if VOICE_RUNTIME_MODE == "remote_daily":
        command = [sys.executable, "-m", "voice_client.runner"]
    else:
        command = [sys.executable, "-m", "voice_bot.bot"]
    process = subprocess.Popen(command, cwd=PROJECT_ROOT, start_new_session=True)
    write_pid(pid_file, process.pid)
    logger.info(
        "Started {} process pid={} command={}",
        VOICE_RUNTIME_MODE,
        process.pid,
        " ".join(command),
    )
    return process


def reap_bot_process(
    process: subprocess.Popen[bytes] | None, pid_file: Path
) -> subprocess.Popen[bytes] | None:
    """Clear finished runtime processes and stale pid tracking.

    Args:
        process: Current runtime subprocess, if any.
        pid_file: Pid file used for runtime process tracking.

    Returns:
        subprocess.Popen[bytes] | None: The still-running process, or `None`
        when the process has exited or was absent.
    """
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
    """Download shared assets and create the openWakeWord detector.

    Args:
        model_name: Pretrained wake-word model name or custom model path.
        vad_threshold: Silero VAD threshold used by openWakeWord.
        inference_framework: `onnx` or `tflite`.

    Returns:
        tuple[Model, str]: Loaded wake-word model instance and resolved model
        name key used in prediction output.
    """
    openwakeword.utils.download_models()
    model = Model(
        wakeword_models=[model_name],
        vad_threshold=vad_threshold,
        inference_framework=inference_framework,
    )
    loaded_name = next(iter(model.models.keys()))
    return model, loaded_name


def resolve_input_device(device: str | None) -> tuple[int | str | None, int, float]:
    """Resolve the input device and native chunk size for microphone capture.

    Args:
        device: Optional device name or index supplied by the user.

    Returns:
        tuple[int | str | None, int, float]: Selected device identifier, native
        chunk size, and input sample rate.
    """
    selected_device = device
    if selected_device is None:
        default_input_device, _ = sd.default.device
        if default_input_device is not None and default_input_device >= 0:
            selected_device = int(default_input_device)

    device_info = sd.query_devices(selected_device, "input")
    input_sample_rate = float(device_info["default_samplerate"])
    input_chunk_size = max(1, int(round(input_sample_rate * CHUNK_SIZE / SAMPLE_RATE)))

    logger.info(
        "Using input device '{}' at {} Hz with chunk size {}",
        device_info["name"],
        input_sample_rate,
        input_chunk_size,
    )

    return selected_device, input_chunk_size, input_sample_rate


def prepare_audio_frame(raw_audio: np.ndarray, input_sample_rate: float) -> np.ndarray:
    """Resample input audio to the wake model's expected sample rate.

    Args:
        raw_audio: Captured mono PCM frame from the input device.
        input_sample_rate: Native sample rate reported by the input device.

    Returns:
        np.ndarray: Audio frame in the wake model's expected sample rate and
        integer PCM format.
    """
    if int(round(input_sample_rate)) == SAMPLE_RATE:
        return raw_audio

    resampled_audio = resampy.resample(
        raw_audio.astype(np.float32), input_sample_rate, SAMPLE_RATE
    )
    return np.clip(np.round(resampled_audio), -32768, 32767).astype(np.int16)


def run_listener(args: argparse.Namespace) -> None:
    """Run the wake-word loop until interrupted by signal.

    Args:
        args: Parsed wake-listener command-line arguments.
    """
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

    input_device, input_chunk_size, input_sample_rate = resolve_input_device(args.device)

    stop_requested = False
    bot_process: subprocess.Popen[bytes] | None = None
    last_trigger_time = 0.0
    audio_buffer = np.array([], dtype=np.int16)

    def request_stop(signum, _frame):
        """Request graceful shutdown after SIGINT or SIGTERM."""
        nonlocal stop_requested
        stop_requested = True
        logger.info("Received signal {}. Stopping wake listener.", signum)

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    while not stop_requested:
        audio_buffer = np.array([], dtype=np.int16)
        with sd.RawInputStream(
            samplerate=input_sample_rate,
            blocksize=input_chunk_size,
            dtype="int16",
            channels=1,
            device=input_device,
        ) as stream:
            while not stop_requested:
                bot_process = reap_bot_process(bot_process, pid_file)
                raw_audio, overflowed = stream.read(input_chunk_size)
                if overflowed:
                    logger.warning("Wake listener audio input overflowed")

                prepared_audio = prepare_audio_frame(
                    np.frombuffer(raw_audio, dtype=np.int16), input_sample_rate
                )
                audio_buffer = np.concatenate((audio_buffer, prepared_audio))

                wake_detected = False
                # Process fixed-size wake-word frames from the rolling audio
                # buffer while keeping device reads at the native sample rate.
                while audio_buffer.size >= CHUNK_SIZE:
                    frame = audio_buffer[:CHUNK_SIZE]
                    audio_buffer = audio_buffer[CHUNK_SIZE:]

                    predictions = model.predict(frame)
                    score = float(predictions.get(loaded_name, 0.0))

                    logger.debug("Wake-word score {}={:.3f}", loaded_name, score)

                    now = time.monotonic()
                    if score < args.threshold:
                        continue
                    if now - last_trigger_time < args.cooldown_secs:
                        logger.info("Wake word detected but cooldown is still active")
                        continue

                    logger.info(
                        "Wake word '{}' detected with score {:.3f}",
                        loaded_name,
                        score,
                    )
                    launched_process = start_bot(pid_file)
                    if launched_process is not None:
                        bot_process = launched_process
                        wake_detected = True
                    last_trigger_time = now
                    break

                if wake_detected:
                    logger.info("Releasing wake listener microphone during session")
                    break

        while bot_process is not None and not stop_requested:
            bot_process = reap_bot_process(bot_process, pid_file)
            if bot_process is not None:
                time.sleep(1)


def main() -> None:
    """CLI entrypoint for the wake listener."""
    args = parse_args()
    configure_logging(args.debug)
    run_listener(args)


if __name__ == "__main__":
    main()
