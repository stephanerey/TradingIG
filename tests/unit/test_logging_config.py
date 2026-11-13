import logging
from io import StringIO
from logging.handlers import TimedRotatingFileHandler

from trading_ig_assistant.utils.logging_config import (
    LOG_FILE_NAME,
    WindowsSafeTimedRotatingFileHandler,
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


def test_windows_failed_rollover_is_deferred_without_dropping_record(
    tmp_path,
    monkeypatch,
) -> None:
    log_path = tmp_path / "locked-rollover.log"
    handler = WindowsSafeTimedRotatingFileHandler(
        log_path,
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.rolloverAt = 0

    def failed_rollover(active_handler) -> None:
        active_handler.stream.close()
        active_handler.stream = None
        raise OSError("simulated Windows rollover failure")

    monkeypatch.setattr(TimedRotatingFileHandler, "doRollover", failed_rollover)
    try:
        handler.emit(
            logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname=__file__,
                lineno=1,
                msg="record survives locked rollover",
                args=(),
                exc_info=None,
            )
        )
        handler.flush()
    finally:
        handler.close()

    assert "record survives locked rollover" in log_path.read_text(encoding="utf-8")
    assert handler.rolloverAt > 0
