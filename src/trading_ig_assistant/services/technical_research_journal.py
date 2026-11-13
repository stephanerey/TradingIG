"""Append-only research journal for deterministic scanner evaluations.

This service records analysis evidence only.  It neither prepares nor transmits
an IG order, and it deliberately excludes raw account identifiers and broker
payloads.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Any

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.analysis import (
    IndicatorSetValue,
    IndicatorValue,
    ScannerResult,
    StrategySignal,
)
from trading_ig_assistant.domain.journal import JournalEvent
from trading_ig_assistant.domain.products import TradableProduct
from trading_ig_assistant.persistence.repositories import JournalEventRepository
from trading_ig_assistant.persistence.sqlite_store import SQLiteStore
from trading_ig_assistant.services.product_context_projection_service import (
    ProductContextProjection,
)
from trading_ig_assistant.services.scanner_runtime_batch_service import (
    ScannerRuntimeBatchResult,
)


class TechnicalResearchJournalError(RuntimeError):
    """Raised with a safe message when the research journal cannot be written."""


@dataclass(frozen=True)
class TechnicalJournalWriteReport:
    appended_events: int
    skipped_events: int


class TechnicalResearchRecorder:
    """Persist scanner evidence without changing scanner or execution behavior."""

    SCHEMA_VERSION = 1

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._repository = JournalEventRepository(store)

    def record(
        self,
        result: ScannerRuntimeBatchResult,
        *,
        environment: IGEnvironment,
        account_id: str | None,
    ) -> TechnicalJournalWriteReport:
        try:
            self._store.initialize()
            events = _events_for_result(
                result,
                environment=environment,
                account_id=account_id,
            )
            existing_ids = self._repository.existing_event_ids(
                tuple(event.event_id for event in events)
            )
            pending = tuple(event for event in events if event.event_id not in existing_ids)
            self._repository.append_many(pending)
        except (OSError, RuntimeError, TypeError, ValueError, sqlite3.Error) as exc:
            raise TechnicalResearchJournalError("technical_journal.write_failed") from exc
        return TechnicalJournalWriteReport(
            appended_events=len(pending),
            skipped_events=len(events) - len(pending),
        )


def _events_for_result(
    result: ScannerRuntimeBatchResult,
    *,
    environment: IGEnvironment,
    account_id: str | None,
) -> tuple[JournalEvent, ...]:
    evaluated_at = result.batch.evaluated_at_utc
    account_ref = _account_ref(environment, account_id)
    correlation_id = _stable_id(
        "technical-batch",
        environment.value,
        account_ref,
        _utc_text(evaluated_at),
    )
    contexts = dict(result.contexts)
    events: list[JournalEvent] = []
    for item in result.batch.items:
        results_by_signal = {
            scanner_result.signal_id: scanner_result
            for scanner_result in item.results
        }
        context = contexts.get(item.product.epic)
        for signal in item.preview.signals:
            event_id = _stable_id(
                "technical-signal",
                environment.value,
                account_ref,
                signal.signal_id,
            )
            payload = {
                "schema_version": TechnicalResearchRecorder.SCHEMA_VERSION,
                "environment": environment.value,
                "evaluation": {
                    "evaluated_at_utc": _utc_text(evaluated_at),
                    "configured_product_epics": result.configured_product_epics,
                },
                "product": _product_payload(item.product),
                "closed_candle_window": {
                    "timeframe": item.preview.timeframe,
                    "used_closed_candles": item.preview.used_closed_candles,
                    "excluded_trailing_candles": item.preview.excluded_trailing_candles,
                    "excluded_pre_gap_candles": item.preview.excluded_pre_gap_candles,
                },
                "signal": _signal_payload(signal),
                "scanner": _scanner_result_payload(results_by_signal.get(signal.signal_id)),
                "indicators": tuple(
                    _indicator_payload(indicator) for indicator in item.preview.indicators
                ),
                "consensus": {
                    "status": item.preview.consensus.status.value,
                    "reason_codes": item.preview.consensus.reason_codes,
                },
                "context": _context_payload(context),
                "limitations": item.preview.limitations,
                "resolved_strategy_profiles": tuple(
                    _json_value(profile) for profile in item.resolved_strategy_profiles
                ),
            }
            events.append(
                JournalEvent(
                    event_id=event_id,
                    timestamp_utc=evaluated_at,
                    event_type="technical_signal_evaluated",
                    correlation_id=correlation_id,
                    account_ref=account_ref,
                    instrument_id=signal.instrument_id,
                    payload=payload,
                )
            )
    for failure in result.batch.failures:
        event_id = _stable_id(
            "technical-failure",
            environment.value,
            account_ref,
            _utc_text(evaluated_at),
            failure.product_epic,
            failure.reason,
        )
        events.append(
            JournalEvent(
                event_id=event_id,
                timestamp_utc=evaluated_at,
                event_type="technical_analysis_failed",
                correlation_id=correlation_id,
                account_ref=account_ref,
                instrument_id=failure.product_epic,
                payload={
                    "schema_version": TechnicalResearchRecorder.SCHEMA_VERSION,
                    "environment": environment.value,
                    "evaluated_at_utc": _utc_text(evaluated_at),
                    "product_epic": failure.product_epic,
                    "reason": failure.reason,
                    "configured_product_epics": result.configured_product_epics,
                },
            )
        )
    return tuple(events)


def _account_ref(environment: IGEnvironment, account_id: str | None) -> str:
    material = f"{environment.value}:{account_id or 'unselected'}"
    fingerprint = sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"ig-{environment.value}:{fingerprint}"


def _stable_id(*parts: str) -> str:
    return sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _product_payload(product: TradableProduct) -> dict[str, Any]:
    return {
        "epic": product.epic,
        "name": product.name,
        "product_type": product.product_type.value,
        "direction": product.direction.value,
        "instrument_type": product.instrument_type,
        "expiry": product.expiry,
        "currency": product.currency,
        "asset_class": product.asset_class.value,
        "status": product.status,
    }


def _signal_payload(signal: StrategySignal) -> dict[str, Any]:
    return {
        "signal_id": signal.signal_id,
        "strategy_id": signal.strategy_id,
        "strategy_version": signal.strategy_version,
        "instrument_id": signal.instrument_id,
        "side": signal.side.value,
        "generated_at_utc": _utc_text(signal.generated_at_utc),
        "valid_until_utc": _utc_text(signal.valid_until_utc),
        "data_state": signal.data_state.value,
        "reason_codes": signal.reason_codes,
        "features": tuple((name, _json_value(value)) for name, value in signal.features),
        "provenance": signal.provenance,
        "entry_zone": (
            tuple(_decimal_text(value) for value in signal.entry_zone)
            if signal.entry_zone is not None
            else None
        ),
        "invalidation": _decimal_text(signal.invalidation),
        "target": _decimal_text(signal.target),
        "confidence_estimate": _decimal_text(signal.confidence_estimate),
        "data_quality": _decimal_text(signal.data_quality),
    }


def _scanner_result_payload(result: ScannerResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "recommendation": result.recommendation.value,
        "ranking_score": _decimal_text(result.ranking_score),
        "components": tuple(
            {
                "name": component.name.value,
                "score": _decimal_text(component.score),
                "weight": _decimal_text(component.weight),
                "reason_codes": component.reason_codes,
                "provenance": component.provenance,
                "veto": component.veto,
                "band": component.band.value if component.band is not None else None,
            }
            for component in result.components
        ),
        "reason_codes": result.reason_codes,
        "commentary": result.commentary,
        "provenance": result.provenance,
        "score_semantics": result.score_semantics,
    }


def _indicator_payload(indicator: IndicatorValue | IndicatorSetValue) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": indicator.name,
        "state": indicator.state.value,
        "required_points": indicator.required_points,
        "observed_points": indicator.observed_points,
        "reason_codes": indicator.reason_codes,
        "provenance": indicator.provenance,
    }
    if isinstance(indicator, IndicatorSetValue):
        payload["values"] = tuple(
            (name, _decimal_text(value)) for name, value in indicator.values
        )
    else:
        payload["value"] = _decimal_text(indicator.value)
    return payload


def _context_payload(context: ProductContextProjection | None) -> dict[str, Any] | None:
    if context is None:
        return None
    return {
        "level": context.level.value,
        "score_band": context.score_band.value,
        "context_score": _decimal_text(context.context_score),
        "components": context.components,
        "reason_codes": context.reason_codes,
        "provenance": context.provenance,
        "safety_veto": context.safety_veto,
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return _utc_text(value)
    if isinstance(value, timedelta):
        return format(Decimal(str(value.total_seconds())).normalize(), "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return tuple(_json_value(item) for item in value)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _json_value(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    return value


def _decimal_text(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Technical journal timestamps must be timezone-aware.")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
