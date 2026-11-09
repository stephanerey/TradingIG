"""Traceable event-driven strategy requiring event, context and post-event price evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from trading_ig_assistant.domain.analysis import (
    DataState,
    EventContextAssessment,
    IndicatorInput,
    IndicatorValue,
    SignalSide,
    StrategyId,
    StrategySignal,
)
from trading_ig_assistant.domain.context_sources import ContextImportance, SourceUsageRights
from trading_ig_assistant.services.indicator_service import atr, momentum
from trading_ig_assistant.services.strategy_clock_service import candle_available_at
from trading_ig_assistant.services.technical_strategy_service import LevelParameters


@dataclass(frozen=True)
class EventDrivenConfig:
    strategy_version: str
    atr_period: int
    momentum_period: int
    minimum_impulse_atr: Decimal
    maximum_gap_atr: Decimal
    maximum_event_age: timedelta
    require_source_url: bool
    levels: LevelParameters
    valid_for: timedelta

    def __post_init__(self) -> None:
        if not self.strategy_version.strip():
            raise ValueError("event strategy version is required")
        if self.atr_period <= 0 or self.momentum_period <= 0:
            raise ValueError("event strategy indicator periods must be positive")
        if self.minimum_impulse_atr <= 0 or self.maximum_gap_atr <= 0:
            raise ValueError("event strategy impulse and gap limits must be positive")
        if self.maximum_event_age <= timedelta(0) or self.valid_for <= timedelta(0):
            raise ValueError("event strategy age and validity must be positive")


class EventDrivenStrategy:
    strategy_id = StrategyId.EVENT_DRIVEN.value

    def __init__(
        self,
        config: EventDrivenConfig,
        context: EventContextAssessment,
    ) -> None:
        self._config = config
        self._context = context

    def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
        decision_at = _decision_time(indicator_input)
        volatility = atr(indicator_input, self._config.atr_period)
        provenance = self._provenance(indicator_input, (volatility,))
        if volatility.state is not DataState.READY:
            return self._flat(
                indicator_input,
                decision_at,
                volatility.state,
                (*volatility.reason_codes, f"{volatility.state.value.upper()}_INDICATORS"),
                provenance,
            )
        assert volatility.value is not None
        if volatility.value <= 0:
            return self._flat(
                indicator_input,
                decision_at,
                DataState.INVALID,
                ("ZERO_ATR",),
                provenance,
            )

        context_rejections = self._context_rejections(decision_at)
        if context_rejections:
            return self._flat(
                indicator_input,
                decision_at,
                DataState.READY,
                context_rejections,
                provenance,
            )

        event_at = self._context.event.scheduled_at_utc
        before = tuple(
            candle
            for candle in indicator_input.candles
            if candle_available_at(candle, indicator_input.timeframe) <= event_at
        )
        after = tuple(
            candle
            for candle in indicator_input.candles
            if event_at < candle_available_at(candle, indicator_input.timeframe) <= decision_at
        )
        if not before or not after:
            return self._flat(
                indicator_input,
                decision_at,
                DataState.WARMING_UP,
                ("EVENT_PRICE_WINDOW_INCOMPLETE",),
                provenance,
            )
        post_event_input = IndicatorInput(
            instrument_id=indicator_input.instrument_id,
            timeframe=indicator_input.timeframe,
            source=indicator_input.source,
            price_basis=indicator_input.price_basis,
            candles=after,
        )
        price_impulse = momentum(post_event_input, self._config.momentum_period)
        provenance = self._provenance(indicator_input, (volatility, price_impulse))
        if price_impulse.state is not DataState.READY:
            return self._flat(
                indicator_input,
                decision_at,
                price_impulse.state,
                (*price_impulse.reason_codes, "POST_EVENT_PRICE_NOT_READY"),
                provenance,
            )
        assert price_impulse.value is not None
        gap_atr = abs(after[0].open - before[-1].close) / volatility.value
        impulse_atr = price_impulse.value / volatility.value
        features: tuple[tuple[str, Decimal | str], ...] = (
            ("event_id", self._context.event.event_id),
            ("event_age_seconds", Decimal((decision_at - event_at).total_seconds())),
            ("gap_atr", gap_atr),
            ("post_event_impulse_atr", impulse_atr),
            ("context_side", self._context.directional_side.value),
        )
        if gap_atr > self._config.maximum_gap_atr:
            return self._flat(
                indicator_input,
                decision_at,
                DataState.READY,
                ("EVENT_GAP_TOO_LARGE",),
                provenance,
                features,
            )
        if (
            self._context.directional_side is SignalSide.BUY
            and impulse_atr >= self._config.minimum_impulse_atr
        ):
            side = SignalSide.BUY
        elif (
            self._context.directional_side is SignalSide.SELL
            and impulse_atr <= -self._config.minimum_impulse_atr
        ):
            side = SignalSide.SELL
        else:
            return self._flat(
                indicator_input,
                decision_at,
                DataState.READY,
                ("POST_EVENT_PRICE_CONFIRMATION_FAILED",),
                provenance,
                features,
            )
        return self._actionable(
            indicator_input,
            decision_at,
            side,
            volatility.value,
            provenance,
            features,
        )

    def _context_rejections(self, decision_at) -> tuple[str, ...]:
        event = self._context.event
        reasons = []
        if event.observed_at_utc > decision_at:
            reasons.append("FUTURE_EVENT_OBSERVATION")
        if event.scheduled_at_utc > decision_at:
            reasons.append("EVENT_NOT_RELEASED")
        elif decision_at - event.scheduled_at_utc > self._config.maximum_event_age:
            reasons.append("EVENT_TOO_OLD")
        if event.importance is not ContextImportance.HIGH:
            reasons.append("EVENT_NOT_HIGH_IMPACT")
        if event.usage_rights is SourceUsageRights.UNKNOWN:
            reasons.append("EVENT_SOURCE_RIGHTS_UNVERIFIED")
        if self._config.require_source_url and event.source_url is None:
            reasons.append("EVENT_SOURCE_URL_REQUIRED")
        if self._context.assessed_at_utc > decision_at:
            reasons.append("FUTURE_DIRECTIONAL_CONTEXT")
        if self._context.valid_until_utc < decision_at:
            reasons.append("DIRECTIONAL_CONTEXT_STALE")
        if self._context.directional_side is SignalSide.FLAT:
            reasons.append("DIRECTIONAL_CONTEXT_UNAVAILABLE")
        return tuple(reasons)

    def _flat(
        self,
        indicator_input: IndicatorInput,
        decision_at,
        state: DataState,
        reasons: tuple[str, ...],
        provenance: tuple[str, ...],
        features: tuple[tuple[str, Decimal | str], ...] = (),
    ) -> StrategySignal:
        return StrategySignal(
            signal_id=self._signal_id(indicator_input, decision_at),
            strategy_id=self.strategy_id,
            strategy_version=self._config.strategy_version,
            instrument_id=indicator_input.instrument_id,
            side=SignalSide.FLAT,
            generated_at_utc=decision_at,
            valid_until_utc=decision_at + self._config.valid_for,
            data_state=state,
            reason_codes=tuple(dict.fromkeys(reasons)),
            features=features,
            provenance=provenance,
            data_quality=Decimal("1") if state is DataState.READY else Decimal("0"),
        )

    def _actionable(
        self,
        indicator_input: IndicatorInput,
        decision_at,
        side: SignalSide,
        atr_value: Decimal,
        provenance: tuple[str, ...],
        features: tuple[tuple[str, Decimal | str], ...],
    ) -> StrategySignal:
        close = indicator_input.candles[-1].close
        zone_distance = atr_value * self._config.levels.entry_zone_atr
        if side is SignalSide.BUY:
            invalidation = close - (atr_value * self._config.levels.stop_atr)
            target = close + (atr_value * self._config.levels.target_atr)
        else:
            invalidation = close + (atr_value * self._config.levels.stop_atr)
            target = close - (atr_value * self._config.levels.target_atr)
        return StrategySignal(
            signal_id=self._signal_id(indicator_input, decision_at),
            strategy_id=self.strategy_id,
            strategy_version=self._config.strategy_version,
            instrument_id=indicator_input.instrument_id,
            side=side,
            generated_at_utc=decision_at,
            valid_until_utc=decision_at + self._config.valid_for,
            data_state=DataState.READY,
            reason_codes=("EVENT_PRICE_AND_CONTEXT_CONFIRMED",),
            features=features,
            provenance=provenance,
            entry_zone=(close - zone_distance, close + zone_distance),
            invalidation=invalidation,
            target=target,
            confidence_estimate=self._context.confidence,
            data_quality=Decimal("1"),
        )

    def _provenance(
        self,
        indicator_input: IndicatorInput,
        indicators: tuple[IndicatorValue, ...],
    ) -> tuple[str, ...]:
        event = self._context.event
        return tuple(
            dict.fromkeys(
                (
                    *indicator_input.provenance(),
                    f"strategy:{self.strategy_id}",
                    f"strategy_version:{self._config.strategy_version}",
                    f"event:{event.event_id}",
                    f"event_source:{event.source}",
                    f"event_rights:{event.usage_rights.value}",
                    f"context_source:{self._context.source}",
                    *(f"context_signal:{item}" for item in self._context.source_signal_ids),
                    f"config:atr_period={self._config.atr_period}",
                    f"config:momentum_period={self._config.momentum_period}",
                    f"config:minimum_impulse_atr={self._config.minimum_impulse_atr}",
                    f"config:maximum_gap_atr={self._config.maximum_gap_atr}",
                    "config:maximum_event_age_seconds="
                    f"{int(self._config.maximum_event_age.total_seconds())}",
                    f"config:require_source_url={str(self._config.require_source_url).lower()}",
                    f"config:entry_zone_atr={self._config.levels.entry_zone_atr}",
                    f"config:stop_atr={self._config.levels.stop_atr}",
                    f"config:target_atr={self._config.levels.target_atr}",
                    *(item for indicator in indicators for item in indicator.provenance),
                )
            )
        )

    def _signal_id(self, indicator_input: IndicatorInput, decision_at) -> str:
        return (
            f"{self.strategy_id}:{indicator_input.instrument_id}:"
            f"{self._context.event.event_id}:{decision_at.isoformat()}"
        )


def _decision_time(indicator_input: IndicatorInput):
    if not indicator_input.candles:
        raise ValueError("event strategy evaluation requires at least one candle")
    return candle_available_at(indicator_input.candles[-1], indicator_input.timeframe)
