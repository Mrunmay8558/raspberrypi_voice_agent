"""Logging helpers for the dashboard FastAPI application."""

import logging
import sys

LOG_FORMAT = (
    "[pid=%(process)s] - [%(asctime)s] - [%(name)s] - "
    "[%(levelname)s] - [%(message)s]"
)


def configure_logger(debug: bool = False) -> None:
    """Configure root Python logging for dashboard modules.

    Args:
        debug: Enables DEBUG level output when true, INFO otherwise.
    """
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)


def logger(name: str) -> logging.Logger:
    """Return a named logger configured through `configure_logger`.

    Args:
        name: Usually the module-level `__name__`.

    Returns:
        A standard-library logger.
    """
    return logging.getLogger(name)
