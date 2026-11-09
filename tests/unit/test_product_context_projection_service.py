from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_ig_assistant.domain.ai_context import (
    AIAnalysisStatus,
    MarketAIAnalysis,
    MarketContextSnapshot,
)
from trading_ig_assistant.domain.analysis import DataState, SignalSide, StrategySignal
from trading_ig_assistant.domain.macro_context import (
    ContextSeverity,
    DirectionalBias,
    EventRisk,
)
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.product_context_projection_service import (
    ProductContextLevel,
    ProductContextProjectionService,
    build_context_score_component,
)

NOW = datetime(2026, 11, 5, 13, 0, tzinfo=UTC)


def _product(*, direction: ProductDirection = ProductDirection.UNKNOWN) -> TradableProduct:
    return TradableProduct(
        epic="IX.D.NASDAQ.OPTCALL2.IP",
        name="US Tech 100 Barrières Achat",
        product_type=ProductType.BARRIER,
        direction=direction,
        asset_class=AssetClass.INDICES,
    )


def _state(
    *,
    index: DirectionalBias,
    event: EventRisk,
):
    empty = MacroContextService().build_state((), NOW)
    return empty.__class__(
        schema_version=empty.schema_version,
        regime=empty.regime,
        index_bias=index,
        gold_bias=empty.gold_bias,
        event_risk=event,
        signals=empty.signals,
        generated_at_utc=empty.generated_at_utc,
        reason_codes=empty.reason_codes,
        provenance=("source:fixture",),
    )


def test_product_context_keeps_missing_inputs_unknown() -> None:
    projection = ProductContextProjectionService().project(
        _product(),
        _state(index=DirectionalBias.UNKNOWN, event=EventRisk.UNKNOWN),
        evaluated_at_utc=NOW,
    )

    assert projection.severity is ContextSeverity.GRAY
    assert projection.level is ProductContextLevel.UNKNOWN
    assert projection.context_score is None
    assert projection.label == "INCONNU"
    assert projection.components == ("index:unknown", "event:unknown", "ai:inactive")


def test_product_context_aligns_localized_buy_barrier_with_bullish_index() -> None:
    projection = ProductContextProjectionService().project(
        _product(),
        _state(index=DirectionalBias.BULLISH, event=EventRisk.LOW),
        evaluated_at_utc=NOW,
    )

    assert projection.severity is ContextSeverity.GREEN
    assert projection.label == "ALIGNÉ"
    assert projection.context_score == Decimal("75")
    assert "index:bullish" in projection.compact_text


def test_high_event_risk_vetoes_favorable_direction() -> None:
    projection = ProductContextProjectionService().project(
        _product(direction=ProductDirection.BUY),
        _state(index=DirectionalBias.BULLISH, event=EventRisk.HIGH),
        evaluated_at_utc=NOW,
    )

    assert projection.severity is ContextSeverity.RED
    assert projection.label == "DÉFAVORABLE"
    assert projection.context_score == Decimal("0")
    assert projection.safety_veto is True
    assert "PRODUCT_EVENT_RED" in projection.reason_codes


def test_scoped_ai_is_applied_only_to_its_product_and_staleness_is_explicit() -> None:
    macro_state = _state(index=DirectionalBias.UNKNOWN, event=EventRisk.UNKNOWN)
    analysis = MarketAIAnalysis(
        status=AIAnalysisStatus.AVAILABLE,
        model_id="openai-responses:test",
        prompt_version="test-v1",
        market_scope=_product().epic,
        directional_bias=DirectionalBias.BEARISH,
        event_risk=EventRisk.LOW,
        confidence=Decimal("0.8"),
        summary="Fixture only",
        risk_flags=(),
        source_signal_ids=("signal:test",),
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=10),
    )
    snapshot = MarketContextSnapshot(
        schema_version=1,
        snapshot_id="snapshot:test",
        instrument_id=_product().epic,
        macro_state=macro_state,
        ai_analysis=analysis,
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=10),
        reason_codes=(),
        provenance=("provider:test",),
    )

    projection = ProductContextProjectionService().project(
        _product(direction=ProductDirection.BUY),
        macro_state,
        evaluated_at_utc=NOW,
        ai_snapshot=snapshot,
    )
    stale = ProductContextProjectionService().project(
        _product(direction=ProductDirection.BUY),
        macro_state,
        evaluated_at_utc=NOW + timedelta(minutes=11),
        ai_snapshot=snapshot,
    )

    assert projection.severity is ContextSeverity.RED
    assert "ai:bearish" in projection.components
    assert stale.severity is ContextSeverity.GRAY
    assert "ai:stale" in stale.components
    expired_at_boundary = ProductContextProjectionService().project(
        _product(direction=ProductDirection.BUY),
        macro_state,
        evaluated_at_utc=NOW + timedelta(minutes=10),
        ai_snapshot=snapshot,
    )
    assert "ai:stale" in expired_at_boundary.components
    future = ProductContextProjectionService().project(
        _product(direction=ProductDirection.BUY),
        macro_state,
        evaluated_at_utc=NOW - timedelta(seconds=1),
        ai_snapshot=snapshot,
    )
    assert future.severity is ContextSeverity.GRAY
    assert "ai:future" in future.components


def test_reference_ai_requires_exact_explicit_product_binding_and_expires() -> None:
    from dataclasses import replace

    from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
    from trading_ig_assistant.domain.markets import CanonicalUnderlyingId

    macro = _state(index=DirectionalBias.UNKNOWN, event=EventRisk.UNKNOWN)
    analysis = MarketAIAnalysis(
        status=AIAnalysisStatus.AVAILABLE,
        model_id="fixture",
        prompt_version="v1",
        market_scope="REFERENCE",
        directional_bias=DirectionalBias.BEARISH,
        event_risk=EventRisk.LOW,
        confidence=Decimal("0.8"),
        summary="Fixture",
        risk_flags=(),
        source_signal_ids=("evidence",),
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=10),
    )
    snapshot = MarketContextSnapshot(
        schema_version=1,
        snapshot_id="S",
        instrument_id="REFERENCE",
        macro_state=macro,
        ai_analysis=analysis,
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=10),
        reason_codes=(),
        provenance=("provider:test",),
    )
    product = _product(direction=ProductDirection.SELL)
    binding = IGProductMarketBinding(
        product_epic=product.epic,
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
        reference_epic="REFERENCE",
        provenance=("mapping:verified",),
    )
    service = ProductContextProjectionService()
    mapped = service.project(
        product, macro, evaluated_at_utc=NOW, ai_snapshot=snapshot, ai_reference_binding=binding
    )
    assert "ai:bearish (référence)" in mapped.components
    assert "mapping:verified" in mapped.provenance
    assert "PRODUCT_AI_GREEN" in mapped.reason_codes
    mismatch = service.project(
        product,
        macro,
        evaluated_at_utc=NOW,
        ai_snapshot=snapshot,
        ai_reference_binding=replace(binding, product_epic="OTHER"),
    )
    assert "ai:not-applicable" in mismatch.components
    unbound = service.project(product, macro, evaluated_at_utc=NOW, ai_snapshot=snapshot)
    assert "ai:not-applicable" in unbound.components
    stale = service.project(
        product,
        macro,
        evaluated_at_utc=NOW + timedelta(minutes=10),
        ai_snapshot=snapshot,
        ai_reference_binding=binding,
    )
    assert "ai:stale (référence)" in stale.components
    assert stale.severity is ContextSeverity.GRAY


def test_low_event_risk_alone_cannot_manufacture_favorable_alignment() -> None:
    projection = ProductContextProjectionService().project(
        _product(direction=ProductDirection.UNKNOWN),
        _state(index=DirectionalBias.UNKNOWN, event=EventRisk.LOW),
        evaluated_at_utc=NOW,
    )

    assert projection.level is ProductContextLevel.UNKNOWN
    assert projection.context_score is None


def test_qualified_event_signal_creates_dark_green_catalyst_score() -> None:
    signal = StrategySignal(
        signal_id="event:confirmed",
        strategy_id="event_driven",
        strategy_version="fixture-v1",
        instrument_id=_product().epic,
        side=SignalSide.BUY,
        generated_at_utc=NOW - timedelta(minutes=1),
        valid_until_utc=NOW + timedelta(minutes=4),
        data_state=DataState.READY,
        reason_codes=("EVENT_PRICE_AND_CONTEXT_CONFIRMED",),
        features=(("event_id", "event:fixture"),),
        provenance=("event:event:fixture", "source:fixture"),
    )
    projection = ProductContextProjectionService().project(
        _product(),
        _state(index=DirectionalBias.BULLISH, event=EventRisk.LOW),
        evaluated_at_utc=NOW,
        qualified_event_signal=signal,
    )
    component = build_context_score_component(projection)

    assert projection.level is ProductContextLevel.CATALYST
    assert projection.label == "CATALYSEUR"
    assert projection.context_score == Decimal("100")
    assert component.score == Decimal("100")
    assert component.weight == Decimal("15")
    assert component.veto is False
    expired = ProductContextProjectionService().project(
        _product(),
        _state(index=DirectionalBias.BULLISH, event=EventRisk.LOW),
        evaluated_at_utc=signal.valid_until_utc,
        qualified_event_signal=signal,
    )
    assert expired.level is not ProductContextLevel.CATALYST


def test_unconfirmed_or_wrong_direction_event_never_becomes_catalyst() -> None:
    signal = StrategySignal(
        signal_id="event:rejected",
        strategy_id="event_driven",
        strategy_version="fixture-v1",
        instrument_id=_product().epic,
        side=SignalSide.SELL,
        generated_at_utc=NOW - timedelta(minutes=1),
        valid_until_utc=NOW + timedelta(minutes=4),
        data_state=DataState.READY,
        reason_codes=("POST_EVENT_PRICE_CONFIRMATION_FAILED",),
        features=(),
        provenance=("event:event:fixture",),
    )
    projection = ProductContextProjectionService().project(
        _product(),
        _state(index=DirectionalBias.BULLISH, event=EventRisk.LOW),
        evaluated_at_utc=NOW,
        qualified_event_signal=signal,
    )

    assert projection.level is ProductContextLevel.ALIGNED
    assert "PRODUCT_EVENT_CATALYST_NOT_QUALIFIED" in projection.reason_codes
