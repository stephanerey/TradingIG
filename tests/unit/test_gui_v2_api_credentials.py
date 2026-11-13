from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from trading_ig_assistant.adapters.credentials import InMemoryApiKeyStore
from trading_ig_assistant.app.config import AppConfig
from trading_ig_assistant.app.qt_api_credentials_controller import ApiCredentialsController
from trading_ig_assistant.services.api_credential_manager import ApiCredentialManager

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def test_settings_saves_tavily_to_secure_store_and_not_config_file(tmp_path: Path) -> None:
    store = InMemoryApiKeyStore()
    manager = ApiCredentialManager(store, environment={})
    path = tmp_path / "config.json"
    config = AppConfig()
    controller = ApiCredentialsController(manager, config, path)
    controller.set_api_key("tavily", "private-tavily-value")

    assert manager.get_api_key("tavily").reveal() == "private-tavily-value"
    assert config.api_providers["tavily"].enabled is True
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["api_providers"]["tavily"]["enabled"] is True
    assert "private-tavily-value" not in path.read_text(encoding="utf-8")
    controller.deleteLater()
