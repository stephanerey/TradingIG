import logging
from io import StringIO

from trading_ig_assistant.utils.logging_config import (
    LOG_FILE_NAME,
    configure_logging,
    emit_session_banner,
)


def test_configure_logging_creates_weekly_rotating_file_handler(tmp_path) -> None:
    log_path = configure_logging(log_dir=tmp_path)

    assert log_path == tmp_path / LOG_FILE_NAME
    assert any(
        getattr(handler, "backupCount", None) == 7
        for handler in logging.getLogger().handlers
        if getattr(handler, "baseFilename", None) == str(log_path)
    )


def test_emit_session_banner_writes_separator() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("trading_ig_assistant.session")
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        emit_session_banner()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    text = stream.getvalue()
    assert "TradingIG session start" in text
    assert "session_id=" in text
