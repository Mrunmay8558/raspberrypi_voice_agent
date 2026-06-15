"""Shell command execution helpers for dashboard services."""

import subprocess

from dashboard.core import logger

logging = logger(__name__)


class CommandError(RuntimeError):
    """Raised when a dashboard-managed shell command fails."""

    def __init__(self, command: list[str], output: str) -> None:
        """Capture the failed command and its output.

        Args:
            command: Shell command that was executed.
            output: Combined stdout/stderr text captured from the process.
        """
        self.command = command
        self.output = output
        super().__init__(output)


def run_command(command: list[str], timeout: int = 20) -> str:
    """Run a command and return combined stdout/stderr text.

    Args:
        command: Command and arguments to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        Combined command output with empty lines removed.

    Raises:
        CommandError: If the command is missing, times out, or exits non-zero.
    """
    logging.debug("Running command: %s", " ".join(command))
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
        logging.warning(output)
        raise CommandError(command, output) from exc
    except subprocess.TimeoutExpired as exc:
        output = f"Command timed out after {timeout}s: {' '.join(command)}"
        logging.warning(output)
        raise CommandError(command, output) from exc

    output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    if completed.returncode != 0:
        logging.warning(
            "Command failed returncode=%s command=%s output=%s",
            completed.returncode,
            " ".join(command),
            output,
        )
        raise CommandError(command, output)
    return output
