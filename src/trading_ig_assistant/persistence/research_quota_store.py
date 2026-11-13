"""Atomic JSON persistence for non-secret research quota counters."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from trading_ig_assistant.domain.market_intelligence import ResearchQuotaState


class JsonResearchQuotaStore:
    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> ResearchQuotaState | None:
        if not self._path.exists():
            return None
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("research quota store is unreadable") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("research quota store schema is unsupported")
        daily = payload.get("daily_credits", {})
        if not isinstance(daily, dict):
            raise ValueError("research quota daily usage must be an object")
        try:
            return ResearchQuotaState(
                month_key=str(payload["month_key"]),
                used_credits=int(payload["used_credits"]),
                daily_credits=tuple(
                    sorted((str(day), int(credits)) for day, credits in daily.items())
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("research quota store content is invalid") from exc

    def save(self, state: ResearchQuotaState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self._path.name}.",
            suffix=".tmp",
            dir=self._path.parent,
            text=True,
        )
        temporary_path = Path(temporary_name)
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "month_key": state.month_key,
            "used_credits": state.used_credits,
            "daily_credits": dict(state.daily_credits),
        }
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self._path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise


def default_research_quota_path(config_path: Path) -> Path:
    return config_path.parent / "data" / "research_quota.json"
