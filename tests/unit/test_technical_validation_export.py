import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.journal import JournalEvent
from trading_ig_assistant.persistence.repositories import JournalEventRepository
from trading_ig_assistant.persistence.sqlite_store import SQLiteStore
from trading_ig_assistant.services.technical_validation_export import (
    TechnicalValidationExporter,
    TechnicalValidationExportError,
)

NOW = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)


def _signal_event() -> JournalEvent:
    return JournalEvent(
        event_id="signal-event-1",
        timestamp_utc=NOW,
        event_type="technical_signal_evaluated",
        correlation_id="batch-1",
        account_ref="ig-live:private-pseudonym",
        instrument_id="IX.TEST.IP",
        payload={
            "environment": "live",
            "signal": {
                "strategy_id": "trend_follow",
                "data_state": "ready",
                "side": "buy",
                "entry_zone": ["100.10", "100.20"],
            },
            "scanner": {"recommendation": "watch", "ranking_score": "75"},
            "indicators": [{"name": "atr_14", "value": "1.2300"}],
        },
        pnl_amount=Decimal("12.34"),
        pnl_currency="EUR",
    )


def _failure_event() -> JournalEvent:
    return JournalEvent(
        event_id="failure-event-1",
        timestamp_utc=NOW,
        event_type="technical_analysis_failed",
        correlation_id="batch-1",
        account_ref="ig-live:private-pseudonym",
        instrument_id="IX.FAIL.IP",
        payload={
            "environment": "live",
            "reason": "configured product unavailable",
        },
    )


def test_export_bundle_is_anonymized_and_summarized(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "journal.sqlite")
    store.initialize()
    repository = JournalEventRepository(store)
    repository.append_many((_signal_event(), _failure_event()))
    destination = tmp_path / "rooms-validation"

    report = TechnicalValidationExporter(store).export_bundle(
        destination,
        generated_at_utc=NOW,
    )

    assert report.event_count == 2
    assert report.signal_count == 1
    assert report.failure_count == 1
    exported = (destination / "technical-events.jsonl").read_text(encoding="utf-8")
    assert "private-pseudonym" not in exported
    assert '"pnl_amount"' not in exported
    assert '"pnl_currency"' not in exported
    rows = [json.loads(line) for line in exported.splitlines()]
    assert rows[0]["payload"]["signal"]["entry_zone"] == ["100.10", "100.20"]
    summary = json.loads((destination / "summary.json").read_text(encoding="utf-8"))
    assert summary["privacy"] == {
        "account_identifier_exported": False,
        "order_or_ticket_data_exported": False,
        "pnl_exported": False,
    }
    assert summary["counts"]["by_data_state"] == {"ready": 1}
    assert summary["counts"]["by_side"] == {"buy": 1}
    assert summary["counts"]["by_strategy"] == {"trend_follow": 1}
    assert summary["counts"]["by_recommendation"] == {"watch": 1}
    assert "pas des probabilités" in (destination / "README.md").read_text(
        encoding="utf-8"
    )


def test_export_refuses_to_overwrite_existing_destination(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "journal.sqlite")
    store.initialize()
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "keep.txt"
    marker.write_text("user data", encoding="utf-8")

    with pytest.raises(
        TechnicalValidationExportError,
        match="technical_validation_export.destination_exists",
    ):
        TechnicalValidationExporter(store).export_bundle(
            destination,
            generated_at_utc=NOW,
        )

    assert marker.read_text(encoding="utf-8") == "user data"


def test_export_requires_utc_timestamp(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "journal.sqlite")

    with pytest.raises(TechnicalValidationExportError):
        TechnicalValidationExporter(store).export_bundle(
            tmp_path / "invalid",
            generated_at_utc=datetime(2026, 11, 12, 15, 0),
        )

    assert not (tmp_path / "invalid").exists()
