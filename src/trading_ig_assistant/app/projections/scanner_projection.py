"""Project the configured reference-market universe without inventing analysis."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from trading_ig_assistant.app.projections.catalogue import CatalogueVM, ProductRowVM
from trading_ig_assistant.app.projections.common import Availability, DataProvenance
from trading_ig_assistant.app.projections.scanner import (
    ScannerIndicatorVM,
    ScannerMarketRowVM,
    ScannerSignalVM,
    ScannerVM,
)
from trading_ig_assistant.domain.analysis import (
    DataState,
    IndicatorSetValue,
    IndicatorValue,
    ScannerRecommendation,
    ScoreComponentName,
    SignalSide,
)
from trading_ig_assistant.domain.market_data import Quote
from trading_ig_assistant.domain.market_navigation import INITIAL_IG_REFERENCE_EPICS
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
)
from trading_ig_assistant.services.scanner_preview_service import (
    default_scanner_strategy_profile,
    required_closed_candles,
)
from trading_ig_assistant.services.scanner_runtime_batch_service import ScannerRuntimeBatchResult

_DEFAULT_REQUIRED_CLOSED_CANDLES = required_closed_candles(
    default_scanner_strategy_profile()
)

_MARKET_NAMES = {
    CanonicalUnderlyingId.US_TECH_100: "US Tech 100",
    CanonicalUnderlyingId.FRANCE_40: "France 40",
    CanonicalUnderlyingId.GERMANY_40: "Allemagne 40",
    CanonicalUnderlyingId.SPOT_GOLD: "Or Spot",
    CanonicalUnderlyingId.US_CRUDE: "Pétrole US",
}

_ASSET_CLASSES = {
    CanonicalUnderlyingId.US_TECH_100: "indices",
    CanonicalUnderlyingId.FRANCE_40: "indices",
    CanonicalUnderlyingId.GERMANY_40: "indices",
    CanonicalUnderlyingId.SPOT_GOLD: "commodities",
    CanonicalUnderlyingId.US_CRUDE: "commodities",
}


def build_scanner_projection(
    *,
    generation_id: int,
    catalogue: CatalogueVM,
    generated_at_utc: datetime,
    previous: ScannerVM | None = None,
) -> ScannerVM:
    """Keep all configured markets visible while analysis is still warming up."""
    products = {row.epic: row for row in catalogue.rows}
    preserve_previous = previous is not None and previous.generation_id == generation_id
    previous_by_id = (
        {}
        if not preserve_previous
        else {row.underlying_id: row for row in previous.rows}
    )
    rows = tuple(
        _row(
            underlying_id,
            reference_epic,
            products.get(reference_epic),
            generated_at_utc,
            previous_by_id.get(underlying_id.value),
        )
        for underlying_id, reference_epic in INITIAL_IG_REFERENCE_EPICS
    )
    return ScannerVM(
        generation_id=generation_id,
        rows=rows,
        availability=(
            previous.availability
            if preserve_previous and previous.availability is Availability.READY
            else (
                Availability.WARMING_UP
                if any(row.bid is not None or row.offer is not None for row in rows)
                else Availability.UNAVAILABLE
            )
        ),
        generated_at_utc=generated_at_utc,
    )


def empty_scanner_projection(generation_id: int, generated_at_utc: datetime) -> ScannerVM:
    return build_scanner_projection(
        generation_id=generation_id,
        catalogue=CatalogueVM(
            generation_id=generation_id,
            query=None,
            rows=(),
            availability=Availability.UNAVAILABLE,
            generated_at_utc=generated_at_utc,
            kind="empty",
        ),
        generated_at_utc=generated_at_utc,
    )


def merge_scanner_reference_quote(
    snapshot: ScannerVM,
    *,
    quote: Quote,
    received_at_utc: datetime,
) -> ScannerVM | None:
    """Merge an attested reference CHART quote without inventing a catalogue product."""
    rows: list[ScannerMarketRowVM] = []
    matched = False
    for row in snapshot.rows:
        if row.reference_epic != quote.epic:
            rows.append(row)
            continue
        matched = True
        rows.append(
            replace(
                row,
                bid=Decimal(str(quote.bid)) if quote.bid is not None else row.bid,
                offer=Decimal(str(quote.offer)) if quote.offer is not None else row.offer,
                net_change=(
                    Decimal(str(quote.net_change))
                    if quote.net_change is not None
                    else row.net_change
                ),
                percent_change=(
                    Decimal(str(quote.percent_change))
                    if quote.percent_change is not None
                    else row.percent_change
                ),
                quote_provenance=DataProvenance(
                    source="ig-lightstreamer",
                    observed_at_utc=_quote_observed_at_utc(quote.timestamp_ms),
                    received_at_utc=received_at_utc,
                    scope=f"ig-chart:{quote.epic}",
                    availability=Availability.READY,
                    reason_codes=("LIVE_REFERENCE_CHART_QUOTE",),
                ),
            )
        )
    if not matched:
        return None
    return replace(
        snapshot,
        rows=tuple(rows),
        availability=Availability.WARMING_UP,
        generated_at_utc=received_at_utc,
    )


def _quote_observed_at_utc(timestamp_ms: int | None) -> datetime | None:
    if timestamp_ms is None or timestamp_ms < 100_000_000_000:
        return None
    try:
        from datetime import UTC

        return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None


def _row(
    underlying_id: CanonicalUnderlyingId,
    reference_epic: str,
    product: ProductRowVM | None,
    generated_at_utc: datetime,
    previous: ScannerMarketRowVM | None,
) -> ScannerMarketRowVM:
    retained_reference_quote = (
        product is None
        and previous is not None
        and previous.quote_provenance.source == "ig-lightstreamer"
        and "LIVE_REFERENCE_CHART_QUOTE" in previous.quote_provenance.reason_codes
    )
    if product is None:
        provenance = (
            previous.quote_provenance
            if retained_reference_quote
            else DataProvenance(
                source="scanner-configured-universe",
                observed_at_utc=None,
                received_at_utc=generated_at_utc,
                scope=f"ig-reference:{reference_epic}",
                availability=Availability.UNAVAILABLE,
                reason_codes=("REFERENCE_QUOTE_UNAVAILABLE",),
            )
        )
    else:
        provenance = product.provenance
    return ScannerMarketRowVM(
        underlying_id=underlying_id.value,
        reference_epic=reference_epic,
        name=_MARKET_NAMES[underlying_id],
        asset_class=_ASSET_CLASSES[underlying_id],
        bid=(
            product.bid
            if product is not None
            else previous.bid if retained_reference_quote else None
        ),
        offer=(
            product.offer
            if product is not None
            else previous.offer if retained_reference_quote else None
        ),
        net_change=(
            product.net_change
            if product is not None
            else previous.net_change if retained_reference_quote else None
        ),
        percent_change=(
            product.percent_change
            if product is not None
            else previous.percent_change if retained_reference_quote else None
        ),
        quote_provenance=provenance,
        technical_score=previous.technical_score if previous is not None else None,
        context_score=previous.context_score if previous is not None else None,
        signal_direction=previous.signal_direction if previous is not None else "unknown",
        recommendation=previous.recommendation if previous is not None else "unavailable",
        observed_candles=previous.observed_candles if previous is not None else 0,
        required_candles=(
            previous.required_candles
            if previous is not None
            else _DEFAULT_REQUIRED_CLOSED_CANDLES
        ),
        reason_codes=previous.reason_codes
        if previous is not None
        else ("SESSION_OHLC_WARMING_UP",),
        evaluated_at_utc=previous.evaluated_at_utc if previous is not None else None,
        strategy_signals=previous.strategy_signals if previous is not None else (),
        context_level=previous.context_level if previous is not None else None,
        context_components=previous.context_components if previous is not None else (),
        context_reason_codes=previous.context_reason_codes if previous is not None else (),
        context_provenance=previous.context_provenance if previous is not None else (),
        context_safety_veto=previous.context_safety_veto if previous is not None else False,
        indicators=previous.indicators if previous is not None else (),
    )


def merge_scanner_candle_progress(
    snapshot: ScannerVM,
    *,
    reference_epic: str,
    observed_candles: int,
    required_candles: int,
    generated_at_utc: datetime,
) -> ScannerVM | None:
    changed = False
    rows = []
    for row in snapshot.rows:
        if row.reference_epic != reference_epic:
            rows.append(row)
            continue
        reason = (
            "ANALYSIS_PENDING"
            if observed_candles >= required_candles
            else "SESSION_OHLC_WARMING_UP"
        )
        warming = observed_candles < required_candles
        updated = replace(
            row,
            observed_candles=observed_candles,
            required_candles=required_candles,
            technical_score=None if warming else row.technical_score,
            context_score=None if warming else row.context_score,
            context_level=None if warming else row.context_level,
            context_components=() if warming else row.context_components,
            context_reason_codes=() if warming else row.context_reason_codes,
            context_provenance=() if warming else row.context_provenance,
            context_safety_veto=False if warming else row.context_safety_veto,
            signal_direction="unknown" if warming else row.signal_direction,
            recommendation="unavailable" if warming else row.recommendation,
            reason_codes=(reason,),
            evaluated_at_utc=None if warming else row.evaluated_at_utc,
            strategy_signals=() if warming else row.strategy_signals,
            indicators=() if warming else row.indicators,
        )
        rows.append(updated)
        changed = updated != row
    if not changed:
        return None
    return replace(
        snapshot,
        rows=tuple(rows),
        availability=Availability.WARMING_UP,
        generated_at_utc=generated_at_utc,
    )


def merge_scanner_analysis(
    snapshot: ScannerVM,
    *,
    result: ScannerRuntimeBatchResult,
    binding_registry: IGProductMarketBindingRegistry,
    generated_at_utc: datetime,
) -> ScannerVM:
    candidates: dict[str, list[tuple[object, object]]] = {}
    indicators_by_underlying: dict[str, list[IndicatorValue | IndicatorSetValue]] = {}
    for item in result.batch.items:
        try:
            binding = binding_registry.resolve(item.product.epic)
        except Exception:
            continue
        indicators_by_underlying.setdefault(binding.canonical_underlying_id.value, []).extend(
            item.preview.indicators
        )
        signals = {signal.signal_id: signal for signal in item.preview.signals}
        for scored in item.results:
            signal = signals.get(scored.signal_id)
            if signal is not None:
                candidates.setdefault(binding.canonical_underlying_id.value, []).append(
                    (scored, signal)
                )

    rows = []
    evaluated_any = False
    for row in snapshot.rows:
        choices = candidates.get(row.underlying_id, [])
        if not choices:
            rows.append(row)
            continue
        scored, selected_signal = min(choices, key=_analysis_sort_key)
        components = {component.name: component for component in scored.components}
        technical = components.get(ScoreComponentName.TECHNICAL)
        context = components.get(ScoreComponentName.CONTEXT)
        try:
            context_projection = result.context_for(selected_signal.instrument_id)
        except KeyError:
            context_projection = None
        rows.append(
            replace(
                row,
                technical_score=technical.score if technical is not None else None,
                context_score=context.score if context is not None else None,
                context_level=(
                    context_projection.level.value
                    if context_projection is not None
                    else None
                ),
                context_components=(
                    context_projection.components
                    if context_projection is not None
                    else ()
                ),
                context_reason_codes=(
                    context_projection.reason_codes
                    if context_projection is not None
                    else ()
                ),
                context_provenance=(
                    context_projection.provenance
                    if context_projection is not None
                    else ()
                ),
                context_safety_veto=(
                    context_projection.safety_veto
                    if context_projection is not None
                    else False
                ),
                signal_direction=_consensus_signal_direction(choices),
                recommendation=scored.recommendation.value,
                reason_codes=scored.reason_codes or ("NO_SCANNER_REASON",),
                evaluated_at_utc=result.batch.evaluated_at_utc,
                strategy_signals=_signal_rows(choices),
                indicators=_indicator_rows(
                    indicators_by_underlying.get(row.underlying_id, [])
                ),
            )
        )
        evaluated_any = True
    return replace(
        snapshot,
        rows=tuple(rows),
        availability=Availability.READY if evaluated_any else snapshot.availability,
        generated_at_utc=generated_at_utc,
    )


def _analysis_sort_key(choice: tuple[object, object]) -> tuple[int, Decimal, str]:
    scored, _signal = choice
    order = {
        ScannerRecommendation.CANDIDATE: 0,
        ScannerRecommendation.WATCH: 1,
        ScannerRecommendation.NO_TRADE: 2,
    }
    ranking = scored.ranking_score if scored.ranking_score is not None else Decimal("-1")
    return order[scored.recommendation], -ranking, scored.signal_id


def _consensus_signal_direction(choices: list[tuple[object, object]]) -> str:
    """Summarize every actionable READY strategy without depending on row order."""
    sides = {
        signal.side
        for _scored, signal in choices
        if signal.data_state is DataState.READY and signal.side is not SignalSide.FLAT
    }
    if sides == {SignalSide.BUY}:
        return "bullish"
    if sides == {SignalSide.SELL}:
        return "bearish"
    return "neutral"


def _signal_rows(choices: list[tuple[object, object]]) -> tuple[ScannerSignalVM, ...]:
    by_id = {}
    for _scored, signal in choices:
        entry_low = signal.entry_zone[0] if signal.entry_zone is not None else None
        entry_high = signal.entry_zone[1] if signal.entry_zone is not None else None
        by_id[signal.signal_id] = ScannerSignalVM(
            signal_id=signal.signal_id,
            product_epic=signal.instrument_id,
            strategy_id=signal.strategy_id,
            side=signal.side.value,
            data_state=signal.data_state.value,
            entry_low=entry_low,
            entry_high=entry_high,
            invalidation=signal.invalidation,
            target=signal.target,
            confidence=signal.confidence_estimate,
            data_quality=signal.data_quality,
            features=signal.features,
            reason_codes=signal.reason_codes,
            provenance=signal.provenance,
            generated_at_utc=signal.generated_at_utc,
            valid_until_utc=signal.valid_until_utc,
        )
    return tuple(
        sorted(
            by_id.values(),
            key=lambda item: (item.strategy_id, item.product_epic, item.signal_id),
        )
    )


def _indicator_rows(
    indicators: list[IndicatorValue | IndicatorSetValue],
) -> tuple[ScannerIndicatorVM, ...]:
    rows: dict[str, ScannerIndicatorVM] = {}
    for indicator in indicators:
        parameters = tuple(
            item
            for item in indicator.provenance
            if item.startswith(
                (
                    "period:",
                    "fast_period:",
                    "slow_period:",
                    "signal_period:",
                    "standard_deviations:",
                    "deviation:",
                )
            )
        )
        values = (
            indicator.values
            if isinstance(indicator, IndicatorSetValue) and indicator.values
            else ((None, indicator.value),)
            if isinstance(indicator, IndicatorValue)
            else ((None, None),)
        )
        for component, value in values:
            indicator_id = ":".join(
                (
                    indicator.name,
                    ",".join(parameters) or "default",
                    component or "value",
                )
            )
            rows[indicator_id] = ScannerIndicatorVM(
                indicator_id=indicator_id,
                name=indicator.name,
                component=component,
                state=indicator.state.value,
                value=value,
                required_points=indicator.required_points,
                observed_points=indicator.observed_points,
                parameters=parameters,
                reason_codes=indicator.reason_codes,
                provenance=indicator.provenance,
            )
    return tuple(
        sorted(
            rows.values(),
            key=lambda item: (item.name, item.parameters, item.component or ""),
        )
    )


def scanner_last_price(row: ScannerMarketRowVM) -> Decimal | None:
    if row.bid is not None and row.offer is not None:
        return (row.bid + row.offer) / Decimal("2")
    return row.bid if row.bid is not None else row.offer
