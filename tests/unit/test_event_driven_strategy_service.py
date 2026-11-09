from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.analysis import (
    AnalysisCandle,
    DataState,
    EventContextAssessment,
    IndicatorInput,
    SignalSide,
)
from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    MacroEvent,
    SourceUsageRights,
)
from trading_ig_assistant.services.event_driven_strategy_service import (
    EventDrivenConfig,
    EventDrivenStrategy,
)
from trading_ig_assistant.services.technical_strategy_service import LevelParameters

START = datetime(2026, 11, 5, 9, 0, tzinfo=UTC)
EVENT_AT = START + timedelta(minutes=3)


def _event(**changes) -> MacroEvent:
    values = {
        "schema_version": 1,
        "event_id": "EVENT-1",
        "title": "Synthetic high-impact event",
        "category": ContextCategory.INFLATION,
        "importance": ContextImportance.HIGH,
        "scheduled_at_utc": EVENT_AT,
        "observed_at_utc": START,
        "source": "Official fixture source",
        "source_url": "https://official.example/event",
        "usage_rights": SourceUsageRights.METADATA_ONLY,
        "tags": ("fixture",),
    }
    values.update(changes)
    return MacroEvent(**values)


def _context(
    *,
    side: SignalSide = SignalSide.BUY,
    event: MacroEvent | None = None,
    assessed_at: datetime = EVENT_AT,
    valid_until: datetime = START + timedelta(minutes=20),
) -> EventContextAssessment:
    selected_event = event or _event()
    return EventContextAssessment(
        event=selected_event,
        directional_side=side,
        assessed_at_utc=assessed_at,
        valid_until_utc=valid_until,
        source="typed-context-fixture",
        source_signal_ids=(selected_event.event_id, "DIRECTION-1"),
        confidence=Decimal("0.6"),
    )


def _config(**changes) -> EventDrivenConfig:
    values = {
        "strategy_version": "event-v1",
        "atr_period": 3,
        "momentum_period": 2,
        "minimum_impulse_atr": Decimal("0.5"),
        "maximum_gap_atr": Decimal("2"),
        "maximum_event_age": timedelta(minutes=10),
        "require_source_url": True,
        "levels": LevelParameters(
            entry_zone_atr=Decimal("0.1"),
            stop_atr=Decimal("1"),
            target_atr=Decimal("2"),
        ),
        "valid_for": timedelta(minutes=3),
    }
    values.update(changes)
    return EventDrivenConfig(**values)


def _input(
    closes: tuple[int, ...],
    *,
    first_post_open: Decimal | None = None,
) -> IndicatorInput:
    candles = []
    for index, raw_close in enumerate(closes):
        close = Decimal(raw_close)
        open_price = first_post_open if index == 3 and first_post_open is not None else close
        candles.append(
            AnalysisCandle(
                timestamp_utc=START + timedelta(minutes=index),
                open=open_price,
                high=max(open_price, close) + Decimal("0.5"),
                low=min(open_price, close) - Decimal("0.5"),
                close=close,
                volume=Decimal("10"),
            )
        )
    return IndicatorInput(
        instrument_id="SYNTHETIC",
        timeframe="M1",
        source="fixture",
        price_basis="mid",
        candles=tuple(candles),
    )


@pytest.mark.parametrize(
    ("closes", "side"),
    (
        ((97, 98, 99, 100, 101, 102, 103, 104), SignalSide.BUY),
        ((104, 103, 102, 101, 100, 99, 98, 97), SignalSide.SELL),
    ),
)
def test_event_strategy_requires_matching_post_event_price_direction(closes, side) -> None:
    signal = EventDrivenStrategy(_config(), _context(side=side)).evaluate(_input(closes))

    assert signal.side is side
    assert signal.data_state is DataState.READY
    assert signal.reason_codes == ("EVENT_PRICE_AND_CONTEXT_CONFIRMED",)
    assert signal.confidence_estimate == Decimal("0.6")
    assert signal.entry_zone is not None
    assert "event:EVENT-1" in signal.provenance
    assert "context_signal:DIRECTION-1" in signal.provenance


def test_unknown_rights_and_stale_context_force_flat() -> None:
    unknown_event = _event(usage_rights=SourceUsageRights.UNKNOWN)
    unknown = EventDrivenStrategy(_config(), _context(event=unknown_event)).evaluate(
        _input((97, 98, 99, 100, 101, 102, 103, 104))
    )
    stale = EventDrivenStrategy(
        _config(),
        _context(valid_until=START + timedelta(minutes=7)),
    ).evaluate(_input((97, 98, 99, 100, 101, 102, 103, 104)))

    assert unknown.side is SignalSide.FLAT
    assert "EVENT_SOURCE_RIGHTS_UNVERIFIED" in unknown.reason_codes
    assert stale.side is SignalSide.FLAT
    assert "DIRECTIONAL_CONTEXT_STALE" in stale.reason_codes


def test_future_old_or_unconfirmed_event_is_rejected() -> None:
    future_event = _event(scheduled_at_utc=START + timedelta(minutes=20))
    future = EventDrivenStrategy(_config(), _context(event=future_event)).evaluate(
        _input((97, 98, 99, 100, 101, 102, 103, 104))
    )
    old_event = _event(scheduled_at_utc=START - timedelta(minutes=30))
    old = EventDrivenStrategy(_config(), _context(event=old_event)).evaluate(
        _input((97, 98, 99, 100, 101, 102, 103, 104))
    )
    no_url_event = _event(source_url=None)
    no_url = EventDrivenStrategy(_config(), _context(event=no_url_event)).evaluate(
        _input((97, 98, 99, 100, 101, 102, 103, 104))
    )

    assert "EVENT_NOT_RELEASED" in future.reason_codes
    assert "EVENT_TOO_OLD" in old.reason_codes
    assert "EVENT_SOURCE_URL_REQUIRED" in no_url.reason_codes


def test_gap_and_contradictory_price_confirmation_are_rejected() -> None:
    gap = EventDrivenStrategy(_config(), _context()).evaluate(
        _input(
            (97, 98, 99, 100, 101, 102, 103, 104),
            first_post_open=Decimal("120"),
        )
    )
    contradiction = EventDrivenStrategy(_config(), _context(side=SignalSide.BUY)).evaluate(
        _input((104, 103, 102, 101, 100, 99, 98, 97))
    )

    assert gap.side is SignalSide.FLAT
    assert gap.reason_codes == ("EVENT_GAP_TOO_LARGE",)
    assert contradiction.side is SignalSide.FLAT
    assert contradiction.reason_codes == ("POST_EVENT_PRICE_CONFIRMATION_FAILED",)


def test_post_event_history_must_be_complete() -> None:
    late_event = _event(scheduled_at_utc=START + timedelta(minutes=7))
    signal = EventDrivenStrategy(_config(), _context(event=late_event)).evaluate(
        _input((97, 98, 99, 100, 101, 102, 103, 104))
    )

    assert signal.side is SignalSide.FLAT
    assert signal.data_state is DataState.WARMING_UP
    assert "INSUFFICIENT_HISTORY" in signal.reason_codes
    assert "POST_EVENT_PRICE_NOT_READY" in signal.reason_codes


def test_event_context_requires_exact_event_lineage() -> None:
    with pytest.raises(ValueError, match="must cite"):
        replace(_context(), source_signal_ids=("OTHER",))


def test_event_config_rejects_nonpositive_limits() -> None:
    with pytest.raises(ValueError, match="impulse and gap"):
        _config(maximum_gap_atr=Decimal("0"))
