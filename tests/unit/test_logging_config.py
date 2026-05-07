import logging

from trading_ig_assistant.utils.logging_config import LOG_FILE_NAME, configure_logging


def test_configure_logging_creates_weekly_rotating_file_handler(tmp_path) -> None:
    log_path = configure_logging(log_dir=tmp_path)

    assert log_path == tmp_path / LOG_FILE_NAME
    assert any(
        getattr(handler, "backupCount", None) == 7
        for handler in logging.getLogger().handlers
        if getattr(handler, "baseFilename", None) == str(log_path)
    )
