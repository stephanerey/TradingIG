import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.analysis import (
    ConsensusStatus,
    DataState,
    IndicatorSetValue,
    IndicatorValue,
    ScannerRecommendation,
    ScannerResult,
    SignalSide,
    StrategyConsensus,
    StrategySignal,
)
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.persistence.repositories import JournalEventRepository
from trading_ig_assistant.persistence.sqlite_store import SQLiteStore
from trading_ig_assistant.services.market_scanner_service import (
    MarketScannerBatch,
    MarketScannerFailure,
    MarketScannerItem,
)
from trading_ig_assistant.services.product_context_projection_service import (
    ProductContextLevel,
    ProductContextProjection,
)
from trading_ig_assistant.services.scanner_preview_service import ScannerPreview
from trading_ig_assistant.services.scanner_profile_resolver import (
    resolve_scanner_strategy_profile,
)
from trading_ig_assistant.services.scanner_runtime_batch_service import (
    ScannerRuntimeBatchResult,
)
from trading_ig_assistant.services.technical_research_journal import (
    TechnicalResearchRecorder,
)

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def _signal(
    suffix: str,
    *,
    side: SignalSide,
    state: DataState,
) -> StrategySignal:
    return StrategySignal(
        signal_id=f"signal-{suffix}",
        strategy_id="trend_follow",
        strategy_version="test-v1",
        instrument_id="IX.TEST.IP",
        side=side,
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=5),
        data_state=state,
        reason_codes=("INSUFFICIENT_HISTORY",) if state is DataState.WARMING_UP else (),
        features=(("ema_fast", Decimal("123.4500")), ("mode", "closed_candles")),
        provenance=("chart:STREAM", "trailing-candle-excluded"),
        entry_zone=(Decimal("123.40"), Decimal("123.50"))
        if side is not SignalSide.FLAT
        else None,
        invalidation=Decimal("122.90") if side is not SignalSide.FLAT else None,
        target=Decimal("124.60") if side is not SignalSide.FLAT else None,
        data_quality=Decimal("0.75"),
    )


def _runtime_result() -> ScannerRuntimeBatchResult:
    warming = _signal("warming", side=SignalSide.FLAT, state=DataState.WARMING_UP)
    ready = _signal("ready", side=SignalSide.BUY, state=DataState.READY)
    preview = ScannerPreview(
        instrument_id="IX.TEST.IP",
        timeframe="M1",
        used_closed_candles=25,
        excluded_trailing_candles=1,
        excluded_pre_gap_candles=2,
        signals=(warming, ready),
        consensus=StrategyConsensus(
            instrument_id="IX.TEST.IP",
            status=ConsensusStatus.SINGLE,
            signals=(warming, ready),
            reason_codes=("SINGLE_ACTIONABLE_SIGNAL",),
        ),
        limitations=("ANALYSIS_ONLY", "NO_TICKET_OR_ORDER_PATH"),
        indicators=(
            IndicatorValue(
                name="atr_14",
                state=DataState.READY,
                value=Decimal("1.2300"),
                required_points=14,
                observed_points=25,
                reason_codes=(),
                provenance=("price_basis:bid",),
            ),
            IndicatorSetValue(
                name="recent_levels_20",
                state=DataState.READY,
                values=(
                    ("support", Decimal("120.10")),
                    ("resistance", Decimal("125.90")),
                ),
                required_points=20,
                observed_points=25,
                reason_codes=(),
                provenance=("price_basis:bid",),
            ),
        ),
    )
    product = TradableProduct(
        epic="IX.TEST.IP",
        name="Test Index",
        product_type=ProductType.BARRIER,
        direction=ProductDirection.BUY,
        currency="EUR",
        status="TRADEABLE",
        asset_class=AssetClass.INDICES,
        raw={"accountId": "RAW-ACCOUNT-MUST-NOT-PERSIST"},
    )
    scanner_result = ScannerResult(
        instrument_id=ready.instrument_id,
        signal_id=ready.signal_id,
        recommendation=ScannerRecommendation.WATCH,
        ranking_score=Decimal("75"),
        components=(),
        reason_codes=("MISSING_CONTEXT",),
        commentary="Ordinal scanner rank; not a probability.",
        provenance=("scanner:test",),
    )
    item = MarketScannerItem(
        product=product,
        preview=preview,
        results=(scanner_result,),
    )
    return ScannerRuntimeBatchResult(
        batch=MarketScannerBatch(
            items=(item,),
            ranked_results=(scanner_result,),
            failures=(
                MarketScannerFailure(
                    product_epic="IX.FAIL.IP",
                    reason="configured product unavailable",
                ),
            ),
            evaluated_at_utc=NOW,
        ),
        contexts=(
            (
                product.epic,
                ProductContextProjection(
                    level=ProductContextLevel.UNKNOWN,
                    components=("Macro context unavailable",),
                    reason_codes=("MISSING_CONTEXT",),
                    provenance=("context:test",),
                ),
            ),
        ),
        configured_product_epics=(product.epic, "IX.FAIL.IP"),
    )


def test_recorder_keeps_explicit_states_and_pseudonymizes_account(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "research.sqlite")
    recorder = TechnicalResearchRecorder(store)

    report = recorder.record(
        _runtime_result(),
        environment=IGEnvironment.LIVE,
        account_id="RAW-ACCOUNT-12345",
    )

    assert report.appended_events == 3
    assert report.skipped_events == 0
    events = JournalEventRepository(store).list_events()
    assert {event.event_type for event in events} == {
        "technical_signal_evaluated",
        "technical_analysis_failed",
    }
    signal_events = [
        event for event in events if event.event_type == "technical_signal_evaluated"
    ]
    assert {event.payload["signal"]["data_state"] for event in signal_events} == {
        "ready",
        "warming_up",
    }
    assert {event.payload["signal"]["side"] for event in signal_events} == {
        "buy",
        "flat",
    }
    ready_event = next(
        event for event in signal_events if event.payload["signal"]["data_state"] == "ready"
    )
    assert ready_event.payload["signal"]["features"][0][1] == "123.4500"
    assert ready_event.payload["indicators"][0]["value"] == "1.2300"
    serialized = json.dumps([event.payload for event in events])
    assert "RAW-ACCOUNT-12345" not in serialized
    assert "RAW-ACCOUNT-MUST-NOT-PERSIST" not in serialized
    assert all(event.account_ref.startswith("ig-live:") for event in events)


def test_recorder_suppresses_deterministic_duplicates_across_instances(tmp_path) -> None:
    database_path = tmp_path / "research.sqlite"
    first = TechnicalResearchRecorder(SQLiteStore(database_path)).record(
        _runtime_result(),
        environment=IGEnvironment.DEMO,
        account_id="ACCOUNT-1",
    )
    second = TechnicalResearchRecorder(SQLiteStore(database_path)).record(
        _runtime_result(),
        environment=IGEnvironment.DEMO,
        account_id="ACCOUNT-1",
    )

    assert first.appended_events == 3
    assert second.appended_events == 0
    assert second.skipped_events == 3


def test_recorder_serializes_real_strategy_profile_durations(tmp_path) -> None:
    runtime_result = _runtime_result()
    resolved_profile = resolve_scanner_strategy_profile()
    profiled_item = replace(
        runtime_result.batch.items[0],
        resolved_strategy_profiles=(resolved_profile,),
    )
    profiled_result = replace(
        runtime_result,
        batch=replace(runtime_result.batch, items=(profiled_item,)),
    )
    store = SQLiteStore(tmp_path / "research.sqlite")

    report = TechnicalResearchRecorder(store).record(
        profiled_result,
        environment=IGEnvironment.LIVE,
        account_id="ACCOUNT-1",
    )

    assert report.appended_events == 3
    signal_event = next(
        event
        for event in JournalEventRepository(store).list_events()
        if event.event_type == "technical_signal_evaluated"
    )
    profile_payload = signal_event.payload["resolved_strategy_profiles"][0]["profile"]
    assert profile_payload["trend_follow"]["valid_for"] == "300"
