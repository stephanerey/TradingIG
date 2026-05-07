"""Application configuration model and JSON loading."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from trading_ig_assistant.adapters.credentials import SecretValue


class IGEnvironment(StrEnum):
    DEMO = "demo"
    LIVE = "live"


@dataclass
class AppConfig:
    environment: IGEnvironment = IGEnvironment.DEMO
    ig_username: str = ""
    ig_password: SecretValue | None = field(default=None, repr=False)
    ig_api_key: SecretValue | None = field(default=None, repr=False)
    selected_account_id: str | None = None
    read_only: bool = True
    enable_live_trading: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.environment, str):
            self.environment = IGEnvironment(self.environment.lower())
        if self.enable_live_trading and self.read_only:
            raise ValueError("enable_live_trading cannot be true while read_only is true.")

    def to_file_dict(self) -> dict[str, Any]:
        """Return a safe representation for disk persistence.

        Secrets are intentionally excluded. They must come from a credential store or
        environment variables during P00.
        """

        return {
            "environment": self.environment.value,
            "ig_username": self.ig_username,
            "selected_account_id": self.selected_account_id,
            "read_only": self.read_only,
            "enable_live_trading": False,
        }

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, Any],
        *,
        allow_live_trading: bool = False,
    ) -> AppConfig:
        requested_live_trading = bool(data.get("enable_live_trading", False))
        enable_live_trading = requested_live_trading and allow_live_trading
        read_only = bool(data.get("read_only", True))
        if not allow_live_trading:
            read_only = True
        return cls(
            environment=IGEnvironment(str(data.get("environment", IGEnvironment.DEMO)).lower()),
            ig_username=str(data.get("ig_username", "")),
            selected_account_id=data.get("selected_account_id") or None,
            read_only=read_only,
            enable_live_trading=enable_live_trading,
        )


def load_config(path: Path, *, allow_live_trading: bool = False) -> AppConfig:
    if not path.exists():
        return AppConfig()
    with path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)
    if not isinstance(data, dict):
        raise ValueError("Configuration file must contain a JSON object.")
    return AppConfig.from_mapping(data, allow_live_trading=allow_live_trading)


def save_config(config: AppConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as config_file:
        json.dump(config.to_file_dict(), config_file, indent=2, sort_keys=True)
        config_file.write("\n")


def default_config_path() -> Path:
    return Path.home() / ".trading_ig_assistant" / "config.json"
