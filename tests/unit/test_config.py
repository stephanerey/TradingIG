from pathlib import Path

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.app.config import AppConfig, IGEnvironment, load_config, save_config


def test_default_config_is_demo_read_only() -> None:
    config = AppConfig()

    assert config.environment == IGEnvironment.DEMO
    assert config.read_only is True
    assert config.enable_live_trading is False


def test_saved_config_excludes_password_and_api_key(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        environment=IGEnvironment.DEMO,
        ig_username="demo-user",
        ig_password=SecretValue("fake-password"),
        ig_api_key=SecretValue("fake-api-key"),
        selected_account_id="SANITIZED_ACCOUNT",
    )

    save_config(config, config_path)

    saved_text = config_path.read_text(encoding="utf-8")
    assert "fake-password" not in saved_text
    assert "fake-api-key" not in saved_text
    assert "ig_password" not in saved_text
    assert "ig_api_key" not in saved_text


def test_config_file_cannot_enable_live_trading_without_explicit_flag(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
        {
          "environment": "live",
          "ig_username": "demo-user",
          "read_only": false,
          "enable_live_trading": true
        }
        """,
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.environment == IGEnvironment.LIVE
    assert config.read_only is True
    assert config.enable_live_trading is False
