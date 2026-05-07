"""Application logging setup with safe rotating file output."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_FILE_NAME = "trading_ig_assistant.log"


def default_log_dir() -> Path:
    return Path.home() / ".trading_ig_assistant" / "logs"


def default_log_path() -> Path:
    return default_log_dir() / LOG_FILE_NAME


def configure_logging(
    *,
    level: int = logging.DEBUG,
    log_dir: Path | None = None,
) -> Path:
    """Configure root logging once and return the active log file path."""

    target_dir = log_dir or default_log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / LOG_FILE_NAME

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    existing_handler = _find_existing_file_handler(root_logger, log_path)
    if existing_handler is None:
        handler = TimedRotatingFileHandler(
            log_path,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(handler)

    logging.getLogger(__name__).debug("Logging configured at %s", log_path)
    return log_path


def _find_existing_file_handler(
    logger: logging.Logger,
    log_path: Path,
) -> TimedRotatingFileHandler | None:
    resolved = log_path.resolve()
    for handler in logger.handlers:
        if isinstance(handler, TimedRotatingFileHandler):
            if Path(handler.baseFilename).resolve() == resolved:
                return handler
    return None
