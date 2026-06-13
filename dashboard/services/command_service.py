import subprocess

from loguru import logger


class CommandError(RuntimeError):
    def __init__(self, command: list[str], output: str) -> None:
        self.command = command
        self.output = output
        super().__init__(output)


def run_command(command: list[str], timeout: int = 20) -> str:
    logger.debug("Running command: {}", " ".join(command))
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        output = f"Command not found: {command[0]}"
        logger.warning(output)
        raise CommandError(command, output) from exc
    except subprocess.TimeoutExpired as exc:
        output = f"Command timed out after {timeout}s: {' '.join(command)}"
        logger.warning(output)
        raise CommandError(command, output) from exc
    output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    if completed.returncode != 0:
        logger.warning(
            "Command failed returncode={} command={} output={}",
            completed.returncode,
            " ".join(command),
            output,
        )
        raise CommandError(command, output)
    return output
