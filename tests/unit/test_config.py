from pathlib import Path

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.app.config import (
    AppConfig,
    IGConnectionProfileConfig,
    IGEnvironment,
    load_config,
    save_config,
)


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


def test_profile_config_saves_non_secret_identifiers_only(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        environment=IGEnvironment.LIVE,
        connection_profiles={
            IGEnvironment.LIVE: IGConnectionProfileConfig(
                environment=IGEnvironment.LIVE,
                identifier="liveuser",
                selected_account_id="LIVE123",
            ),
            IGEnvironment.DEMO: IGConnectionProfileConfig(
                environment=IGEnvironment.DEMO,
                identifier="demouser",
                selected_account_id="DEMO123",
            ),
        },
    )

    save_config(config, config_path)
    saved_text = config_path.read_text(encoding="utf-8")
    loaded = load_config(config_path)

    assert "password" not in saved_text.lower()
    assert "api_key" not in saved_text.lower()
    assert loaded.connection_profiles[IGEnvironment.LIVE].identifier == "liveuser"
    assert loaded.connection_profiles[IGEnvironment.DEMO].selected_account_id == "DEMO123"


def test_config_persists_last_selected_product_epic(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        environment=IGEnvironment.LIVE,
        last_selected_product_epic="IX.D.NASDAQ.IFD.IP",
    )

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded.last_selected_product_epic == "IX.D.NASDAQ.IFD.IP"


def test_config_persists_chart_source_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = AppConfig(
        environment=IGEnvironment.LIVE,
        chart_source_overrides={"us tech 100": "IX.D.NASDAQ.IFD.IP"},
    )

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded.chart_source_overrides == {"us tech 100": "IX.D.NASDAQ.IFD.IP"}
