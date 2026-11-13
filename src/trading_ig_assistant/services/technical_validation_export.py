"""Sanitized export bundle for collaborative technical-signal validation."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_ig_assistant.domain.journal import JournalEvent
from trading_ig_assistant.persistence.repositories import JournalEventRepository
from trading_ig_assistant.persistence.sqlite_store import SQLiteStore

TECHNICAL_EVENT_TYPES = frozenset(
    {"technical_signal_evaluated", "technical_analysis_failed"}
)


class TechnicalValidationExportError(RuntimeError):
    """Raised with a non-sensitive message when a bundle cannot be exported."""


@dataclass(frozen=True)
class TechnicalValidationExportReport:
    bundle_directory: Path
    event_count: int
    signal_count: int
    failure_count: int


class TechnicalValidationExporter:
    """Export technical research events without broker account or P&L data."""

    FORMAT_VERSION = 1

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._repository = JournalEventRepository(store)

    def export_bundle(
        self,
        destination: Path,
        *,
        generated_at_utc: datetime | None = None,
    ) -> TechnicalValidationExportReport:
        generated_at = generated_at_utc or datetime.now(UTC)
        try:
            _require_utc(generated_at)
        except ValueError as exc:
            raise TechnicalValidationExportError(
                "technical_validation_export.failed"
            ) from exc
        destination = Path(destination)
        if destination.exists():
            raise TechnicalValidationExportError(
                "technical_validation_export.destination_exists"
            )
        try:
            self._store.initialize()
            events = tuple(
                event
                for event in self._repository.list_events()
                if event.event_type in TECHNICAL_EVENT_TYPES
            )
            summary = _summary(events, generated_at)
            parent = destination.parent
            parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(
                tempfile.mkdtemp(prefix=".tradingig-validation-", dir=parent)
            )
            try:
                _write_jsonl(temporary / "technical-events.jsonl", events)
                (temporary / "summary.json").write_text(
                    json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n",
                    encoding="utf-8",
                )
                (temporary / "README.md").write_text(
                    _readme(events, generated_at),
                    encoding="utf-8",
                )
                temporary.replace(destination)
            except Exception:
                shutil.rmtree(temporary, ignore_errors=True)
                raise
        except TechnicalValidationExportError:
            raise
        except (OSError, RuntimeError, TypeError, ValueError, sqlite3.Error) as exc:
            raise TechnicalValidationExportError(
                "technical_validation_export.failed"
            ) from exc
        return TechnicalValidationExportReport(
            bundle_directory=destination,
            event_count=len(events),
            signal_count=sum(
                event.event_type == "technical_signal_evaluated" for event in events
            ),
            failure_count=sum(
                event.event_type == "technical_analysis_failed" for event in events
            ),
        )


def _write_jsonl(path: Path, events: tuple[JournalEvent, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(
                json.dumps(
                    _export_event(event),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )


def _export_event(event: JournalEvent) -> dict[str, Any]:
    return {
        "format_version": TechnicalValidationExporter.FORMAT_VERSION,
        "event_id": event.event_id,
        "timestamp_utc": event.timestamp_text(),
        "event_type": event.event_type,
        "correlation_id": event.correlation_id,
        "instrument_id": event.instrument_id,
        "payload": event.payload,
    }


def _summary(events: tuple[JournalEvent, ...], generated_at: datetime) -> dict[str, Any]:
    signals = tuple(
        event for event in events if event.event_type == "technical_signal_evaluated"
    )
    failures = tuple(
        event for event in events if event.event_type == "technical_analysis_failed"
    )
    return {
        "format_version": TechnicalValidationExporter.FORMAT_VERSION,
        "generated_at_utc": _utc_text(generated_at),
        "privacy": {
            "account_identifier_exported": False,
            "pnl_exported": False,
            "order_or_ticket_data_exported": False,
        },
        "counts": {
            "events": len(events),
            "signals": len(signals),
            "failures": len(failures),
            "by_environment": _counter(signals, "environment"),
            "by_strategy": _nested_counter(signals, "signal", "strategy_id"),
            "by_data_state": _nested_counter(signals, "signal", "data_state"),
            "by_side": _nested_counter(signals, "signal", "side"),
            "by_recommendation": _nested_counter(
                signals, "scanner", "recommendation"
            ),
        },
    }


def _counter(events: tuple[JournalEvent, ...], key: str) -> dict[str, int]:
    counts = Counter(str(event.payload.get(key, "unknown")) for event in events)
    return dict(sorted(counts.items()))


def _nested_counter(
    events: tuple[JournalEvent, ...],
    parent: str,
    key: str,
) -> dict[str, int]:
    values: list[str] = []
    for event in events:
        candidate = event.payload.get(parent)
        if isinstance(candidate, dict):
            value = candidate.get(key)
        else:
            value = None
        values.append(str(value) if value is not None else "unknown")
    return dict(sorted(Counter(values).items()))


def _readme(events: tuple[JournalEvent, ...], generated_at: datetime) -> str:
    return (
        "# TradingIG — paquet de validation technique\n\n"
        f"Généré en UTC : `{_utc_text(generated_at)}`  \n"
        f"Événements techniques : **{len(events)}**\n\n"
        "Ce paquet sert à l’analyse post-mortem des valeurs suivies. "
        "Il ne contient aucun identifiant de compte IG, PnL, ticket, ordre, "
        "position ou secret. Les scores du scanner sont des rangs explicables, "
        "pas des probabilités.\n\n"
        "## Fichiers\n\n"
        "- `technical-events.jsonl` : événements append-only détaillés.\n"
        "- `summary.json` : compteurs de contrôle et déclaration de confidentialité.\n\n"
        "## Points de validation suggérés\n\n"
        "- signal présent ou manqué ;\n"
        "- entrée, invalidation et objectif cohérents avec les bougies closes ;\n"
        "- état READY, WARMING_UP, INVALID ou NO_TRADE correctement conservé ;\n"
        "- indicateurs et provenance suffisants pour reproduire la décision.\n"
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("Export timestamps must use UTC.")


def _utc_text(value: datetime) -> str:
    _require_utc(value)
    return value.isoformat().replace("+00:00", "Z")
