"""Configurable deterministic technical strategies with no broker or ticket dependency."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from trading_ig_assistant.domain.analysis import (
    DataState,
    IndicatorInput,
    IndicatorSetValue,
    IndicatorValue,
    SignalSide,
    StrategyId,
    StrategySignal,
)
from trading_ig_assistant.services.indicator_service import (
    atr,
    ema,
    recent_levels,
    rsi,
    volume_ratio,
)
from trading_ig_assistant.services.strategy_clock_service import candle_available_at


@dataclass(frozen=True)
class LevelParameters:
    entry_zone_atr: Decimal
    stop_atr: Decimal
    target_atr: Decimal

    def __post_init__(self) -> None:
        if self.entry_zone_atr < 0 or self.stop_atr <= 0 or self.target_atr <= 0:
            raise ValueError("strategy ATR level parameters are invalid")


@dataclass(frozen=True)
class TrendFollowConfig:
    strategy_version: str
    fast_ema_period: int
    slow_ema_period: int
    slope_lookback: int
    atr_period: int
    max_extension_atr: Decimal
    levels: LevelParameters
    valid_for: timedelta

    def __post_init__(self) -> None:
        _validate_common(self.strategy_version, self.atr_period, self.valid_for)
        if self.fast_ema_period <= 0 or self.slow_ema_period <= self.fast_ema_period:
            raise ValueError("trend EMA periods must satisfy 0 < fast < slow")
        if self.slope_lookback <= 0 or self.max_extension_atr <= 0:
            raise ValueError("trend slope and extension parameters must be positive")


@dataclass(frozen=True)
class BreakoutConfig:
    strategy_version: str
    level_lookback: int
    atr_period: int
    minimum_breakout_atr: Decimal
    maximum_extension_atr: Decimal
    maximum_atr_percent: Decimal
    volume_period: int | None
    minimum_volume_ratio: Decimal | None
    levels: LevelParameters
    valid_for: timedelta

    def __post_init__(self) -> None:
        _validate_common(self.strategy_version, self.atr_period, self.valid_for)
        if self.level_lookback <= 1:
            raise ValueError("breakout level lookback must exceed one")
        if (
            self.minimum_breakout_atr <= 0
            or self.maximum_extension_atr < self.minimum_breakout_atr
            or self.maximum_atr_percent <= 0
        ):
            raise ValueError("breakout ATR thresholds are invalid")
        paired = (self.volume_period is None, self.minimum_volume_ratio is None)
        if paired not in {(True, True), (False, False)}:
            raise ValueError("breakout volume period and threshold must be configured together")
        if self.volume_period is not None and self.volume_period <= 0:
            raise ValueError("breakout volume period must be positive")
        if self.minimum_volume_ratio is not None and self.minimum_volume_ratio <= 0:
            raise ValueError("breakout minimum volume ratio must be positive")


@dataclass(frozen=True)
class PullbackConfig:
    strategy_version: str
    fast_ema_period: int
    slow_ema_period: int
    rsi_period: int
    atr_period: int
    maximum_distance_atr: Decimal
    buy_rsi_range: tuple[Decimal, Decimal]
    sell_rsi_range: tuple[Decimal, Decimal]
    levels: LevelParameters
    valid_for: timedelta

    def __post_init__(self) -> None:
        _validate_common(self.strategy_version, self.atr_period, self.valid_for)
        if self.fast_ema_period <= 0 or self.slow_ema_period <= self.fast_ema_period:
            raise ValueError("pullback EMA periods must satisfy 0 < fast < slow")
        if self.rsi_period <= 0 or self.maximum_distance_atr <= 0:
            raise ValueError("pullback RSI and distance parameters must be positive")
        for label, bounds in (("buy", self.buy_rsi_range), ("sell", self.sell_rsi_range)):
            if not Decimal("0") <= bounds[0] <= bounds[1] <= Decimal("100"):
                raise ValueError(f"pullback {label} RSI range is invalid")


class TrendFollowStrategy:
    strategy_id = StrategyId.TREND_FOLLOW.value

    def __init__(self, config: TrendFollowConfig) -> None:
        self._config = config

    def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
        generated_at = _decision_time(indicator_input)
        configuration = _configuration_provenance(self._config)
        fast = ema(indicator_input, self._config.fast_ema_period)
        slow = ema(indicator_input, self._config.slow_ema_period)
        volatility = atr(indicator_input, self._config.atr_period)
        previous_input = _without_latest(indicator_input, self._config.slope_lookback)
        previous_slow = ema(previous_input, self._config.slow_ema_period)
        indicators = (fast, slow, volatility, previous_slow)
        not_ready = _not_ready_signal(
            self.strategy_id,
            self._config.strategy_version,
            indicator_input,
            generated_at,
            self._config.valid_for,
            indicators,
            configuration,
        )
        if not_ready is not None:
            return not_ready
        assert fast.value is not None
        assert slow.value is not None
        assert volatility.value is not None
        assert previous_slow.value is not None
        if volatility.value <= 0:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.INVALID,
                ("ZERO_ATR",),
                indicators,
                configuration=configuration,
            )
        close = indicator_input.candles[-1].close
        slope = slow.value - previous_slow.value
        if fast.value > slow.value and slope > 0:
            side = SignalSide.BUY
        elif fast.value < slow.value and slope < 0:
            side = SignalSide.SELL
        else:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.READY,
                ("TREND_NOT_ALIGNED",),
                indicators,
                configuration=configuration,
                features=(("fast_ema", fast.value), ("slow_ema", slow.value), ("slope", slope)),
            )
        extension = abs(close - fast.value) / volatility.value
        features = (
            ("fast_ema", fast.value),
            ("slow_ema", slow.value),
            ("slow_ema_slope", slope),
            ("atr", volatility.value),
            ("extension_atr", extension),
        )
        if extension > self._config.max_extension_atr:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.READY,
                ("SIGNAL_TOO_EXTENDED",),
                indicators,
                configuration=configuration,
                features=features,
            )
        return _actionable_signal(
            self.strategy_id,
            self._config.strategy_version,
            indicator_input,
            generated_at,
            self._config.valid_for,
            side,
            self._config.levels,
            volatility.value,
            features,
            indicators,
            configuration,
            ("TREND_CONFIRMED",),
        )


class BreakoutStrategy:
    strategy_id = StrategyId.BREAKOUT.value

    def __init__(self, config: BreakoutConfig) -> None:
        self._config = config

    def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
        generated_at = _decision_time(indicator_input)
        configuration = _configuration_provenance(self._config)
        prior_input = _without_latest(indicator_input, 1)
        levels = recent_levels(prior_input, self._config.level_lookback)
        volatility = atr(indicator_input, self._config.atr_period)
        volume = (
            volume_ratio(indicator_input, self._config.volume_period)
            if self._config.volume_period is not None
            else None
        )
        indicators = (levels, volatility, *((volume,) if volume is not None else ()))
        not_ready = _not_ready_signal(
            self.strategy_id,
            self._config.strategy_version,
            indicator_input,
            generated_at,
            self._config.valid_for,
            indicators,
            configuration,
        )
        if not_ready is not None:
            return not_ready
        level_values = dict(levels.values)
        assert volatility.value is not None
        if volatility.value <= 0:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.INVALID,
                ("ZERO_ATR",),
                indicators,
                configuration=configuration,
            )
        close = indicator_input.candles[-1].close
        if close == 0:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.INVALID,
                ("ZERO_CLOSE",),
                indicators,
                configuration=configuration,
            )
        support = level_values["support"]
        resistance = level_values["resistance"]
        buy_distance = close - resistance
        sell_distance = support - close
        minimum = volatility.value * self._config.minimum_breakout_atr
        if buy_distance >= minimum:
            side = SignalSide.BUY
            distance = buy_distance
        elif sell_distance >= minimum:
            side = SignalSide.SELL
            distance = sell_distance
        else:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.READY,
                ("NO_CONFIRMED_BREAKOUT",),
                indicators,
                configuration=configuration,
                features=(
                    ("support", support),
                    ("resistance", resistance),
                    ("atr", volatility.value),
                ),
            )
        extension = distance / volatility.value
        atr_percent = (volatility.value / abs(close)) * Decimal("100")
        features: tuple[tuple[str, Decimal | str], ...] = (
            ("support", support),
            ("resistance", resistance),
            ("atr", volatility.value),
            ("breakout_distance_atr", extension),
            ("atr_percent", atr_percent),
        )
        if extension > self._config.maximum_extension_atr:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.READY,
                ("BREAKOUT_TOO_EXTENDED",),
                indicators,
                configuration=configuration,
                features=features,
            )
        if atr_percent > self._config.maximum_atr_percent:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.READY,
                ("EXTREME_VOLATILITY",),
                indicators,
                configuration=configuration,
                features=features,
            )
        if volume is not None:
            assert volume.value is not None
            features = (*features, ("volume_ratio", volume.value))
            assert self._config.minimum_volume_ratio is not None
            if volume.value < self._config.minimum_volume_ratio:
                return _flat_signal(
                    self.strategy_id,
                    self._config.strategy_version,
                    indicator_input,
                    generated_at,
                    self._config.valid_for,
                    DataState.READY,
                    ("VOLUME_CONFIRMATION_FAILED",),
                    indicators,
                    configuration=configuration,
                    features=features,
                )
        return _actionable_signal(
            self.strategy_id,
            self._config.strategy_version,
            indicator_input,
            generated_at,
            self._config.valid_for,
            side,
            self._config.levels,
            volatility.value,
            features,
            indicators,
            configuration,
            ("BREAKOUT_CONFIRMED",),
        )


class PullbackStrategy:
    strategy_id = StrategyId.PULLBACK.value

    def __init__(self, config: PullbackConfig) -> None:
        self._config = config

    def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
        generated_at = _decision_time(indicator_input)
        configuration = _configuration_provenance(self._config)
        fast = ema(indicator_input, self._config.fast_ema_period)
        slow = ema(indicator_input, self._config.slow_ema_period)
        oscillator = rsi(indicator_input, self._config.rsi_period)
        volatility = atr(indicator_input, self._config.atr_period)
        indicators = (fast, slow, oscillator, volatility)
        not_ready = _not_ready_signal(
            self.strategy_id,
            self._config.strategy_version,
            indicator_input,
            generated_at,
            self._config.valid_for,
            indicators,
            configuration,
        )
        if not_ready is not None:
            return not_ready
        assert fast.value is not None
        assert slow.value is not None
        assert oscillator.value is not None
        assert volatility.value is not None
        if volatility.value <= 0:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.INVALID,
                ("ZERO_ATR",),
                indicators,
                configuration=configuration,
            )
        current = indicator_input.candles[-1]
        previous = indicator_input.candles[-2]
        distance = abs(current.close - fast.value) / volatility.value
        features = (
            ("fast_ema", fast.value),
            ("slow_ema", slow.value),
            ("rsi", oscillator.value),
            ("atr", volatility.value),
            ("distance_from_fast_atr", distance),
        )
        if distance > self._config.maximum_distance_atr:
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.READY,
                ("NO_PULLBACK_ZONE",),
                indicators,
                configuration=configuration,
                features=features,
            )
        buy_rsi = self._config.buy_rsi_range[0] <= oscillator.value <= self._config.buy_rsi_range[1]
        sell_rsi = (
            self._config.sell_rsi_range[0] <= oscillator.value <= self._config.sell_rsi_range[1]
        )
        if (
            fast.value > slow.value
            and current.close > slow.value
            and current.close > previous.close
            and buy_rsi
        ):
            side = SignalSide.BUY
        elif (
            fast.value < slow.value
            and current.close < slow.value
            and current.close < previous.close
            and sell_rsi
        ):
            side = SignalSide.SELL
        else:
            reasons = []
            if not (
                (fast.value > slow.value and current.close > slow.value)
                or (fast.value < slow.value and current.close < slow.value)
            ):
                reasons.append("TREND_OR_STRUCTURE_INVALID")
            if not (current.close > previous.close or current.close < previous.close):
                reasons.append("MISSING_PRICE_CONFIRMATION")
            if not (buy_rsi or sell_rsi):
                reasons.append("RSI_CONFIRMATION_FAILED")
            if not reasons:
                reasons.append("PULLBACK_NOT_CONFIRMED")
            return _flat_signal(
                self.strategy_id,
                self._config.strategy_version,
                indicator_input,
                generated_at,
                self._config.valid_for,
                DataState.READY,
                tuple(reasons),
                indicators,
                configuration=configuration,
                features=features,
            )
        return _actionable_signal(
            self.strategy_id,
            self._config.strategy_version,
            indicator_input,
            generated_at,
            self._config.valid_for,
            side,
            self._config.levels,
            volatility.value,
            features,
            indicators,
            configuration,
            ("PULLBACK_CONFIRMED",),
        )


IndicatorResult = IndicatorValue | IndicatorSetValue


def _validate_common(strategy_version: str, atr_period: int, valid_for: timedelta) -> None:
    if not strategy_version.strip():
        raise ValueError("strategy version is required")
    if atr_period <= 0 or valid_for <= timedelta(0):
        raise ValueError("strategy ATR period and validity must be positive")


def _decision_time(indicator_input: IndicatorInput):
    if not indicator_input.candles:
        raise ValueError("strategy evaluation requires at least one candle")
    return candle_available_at(indicator_input.candles[-1], indicator_input.timeframe)


def _without_latest(indicator_input: IndicatorInput, count: int) -> IndicatorInput:
    candles = indicator_input.candles[:-count] if count < len(indicator_input.candles) else ()
    return IndicatorInput(
        instrument_id=indicator_input.instrument_id,
        timeframe=indicator_input.timeframe,
        source=indicator_input.source,
        price_basis=indicator_input.price_basis,
        candles=candles,
    )


def _not_ready_signal(
    strategy_id: str,
    strategy_version: str,
    indicator_input: IndicatorInput,
    generated_at,
    valid_for: timedelta,
    indicators: tuple[IndicatorResult, ...],
    configuration: tuple[str, ...],
) -> StrategySignal | None:
    invalid = tuple(item for item in indicators if item.state is DataState.INVALID)
    warming = tuple(item for item in indicators if item.state is DataState.WARMING_UP)
    selected = invalid or warming
    if not selected:
        return None
    state = DataState.INVALID if invalid else DataState.WARMING_UP
    reasons = tuple(
        dict.fromkeys(
            (
                *(reason for item in selected for reason in item.reason_codes),
                f"{state.value.upper()}_INDICATORS",
            )
        )
    )
    return _flat_signal(
        strategy_id,
        strategy_version,
        indicator_input,
        generated_at,
        valid_for,
        state,
        reasons,
        indicators,
        configuration=configuration,
    )


def _flat_signal(
    strategy_id: str,
    strategy_version: str,
    indicator_input: IndicatorInput,
    generated_at,
    valid_for: timedelta,
    data_state: DataState,
    reason_codes: tuple[str, ...],
    indicators: tuple[IndicatorResult, ...],
    *,
    configuration: tuple[str, ...] = (),
    features: tuple[tuple[str, Decimal | str], ...] = (),
) -> StrategySignal:
    return StrategySignal(
        signal_id=_signal_id(strategy_id, indicator_input.instrument_id, generated_at),
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        instrument_id=indicator_input.instrument_id,
        side=SignalSide.FLAT,
        generated_at_utc=generated_at,
        valid_until_utc=generated_at + valid_for,
        data_state=data_state,
        reason_codes=reason_codes,
        features=features,
        provenance=_provenance(
            indicator_input,
            strategy_id,
            strategy_version,
            indicators,
            configuration,
        ),
        data_quality=Decimal("1") if data_state is DataState.READY else Decimal("0"),
    )


def _actionable_signal(
    strategy_id: str,
    strategy_version: str,
    indicator_input: IndicatorInput,
    generated_at,
    valid_for: timedelta,
    side: SignalSide,
    levels: LevelParameters,
    atr_value: Decimal,
    features: tuple[tuple[str, Decimal | str], ...],
    indicators: tuple[IndicatorResult, ...],
    configuration: tuple[str, ...],
    reason_codes: tuple[str, ...],
) -> StrategySignal:
    close = indicator_input.candles[-1].close
    zone_distance = atr_value * levels.entry_zone_atr
    if side is SignalSide.BUY:
        invalidation = close - (atr_value * levels.stop_atr)
        target = close + (atr_value * levels.target_atr)
    else:
        invalidation = close + (atr_value * levels.stop_atr)
        target = close - (atr_value * levels.target_atr)
    return StrategySignal(
        signal_id=_signal_id(strategy_id, indicator_input.instrument_id, generated_at),
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        instrument_id=indicator_input.instrument_id,
        side=side,
        generated_at_utc=generated_at,
        valid_until_utc=generated_at + valid_for,
        data_state=DataState.READY,
        reason_codes=reason_codes,
        features=features,
        provenance=_provenance(
            indicator_input,
            strategy_id,
            strategy_version,
            indicators,
            configuration,
        ),
        entry_zone=(close - zone_distance, close + zone_distance),
        invalidation=invalidation,
        target=target,
        confidence_estimate=None,
        data_quality=Decimal("1"),
    )


def _provenance(
    indicator_input: IndicatorInput,
    strategy_id: str,
    strategy_version: str,
    indicators: tuple[IndicatorResult, ...],
    configuration: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                *indicator_input.provenance(),
                f"strategy:{strategy_id}",
                f"strategy_version:{strategy_version}",
                *configuration,
                *(item for indicator in indicators for item in indicator.provenance),
            )
        )
    )


def _signal_id(strategy_id: str, instrument_id: str, generated_at) -> str:
    return f"{strategy_id}:{instrument_id}:{generated_at.isoformat()}"


def _configuration_provenance(
    config: TrendFollowConfig | BreakoutConfig | PullbackConfig,
) -> tuple[str, ...]:
    common = (
        f"config:atr_period={config.atr_period}",
        f"config:valid_for_seconds={int(config.valid_for.total_seconds())}",
        f"config:entry_zone_atr={config.levels.entry_zone_atr}",
        f"config:stop_atr={config.levels.stop_atr}",
        f"config:target_atr={config.levels.target_atr}",
    )
    if isinstance(config, TrendFollowConfig):
        specific = (
            f"config:fast_ema_period={config.fast_ema_period}",
            f"config:slow_ema_period={config.slow_ema_period}",
            f"config:slope_lookback={config.slope_lookback}",
            f"config:max_extension_atr={config.max_extension_atr}",
        )
    elif isinstance(config, BreakoutConfig):
        specific = (
            f"config:level_lookback={config.level_lookback}",
            f"config:minimum_breakout_atr={config.minimum_breakout_atr}",
            f"config:maximum_extension_atr={config.maximum_extension_atr}",
            f"config:maximum_atr_percent={config.maximum_atr_percent}",
            f"config:volume_period={config.volume_period}",
            f"config:minimum_volume_ratio={config.minimum_volume_ratio}",
        )
    else:
        specific = (
            f"config:fast_ema_period={config.fast_ema_period}",
            f"config:slow_ema_period={config.slow_ema_period}",
            f"config:rsi_period={config.rsi_period}",
            f"config:maximum_distance_atr={config.maximum_distance_atr}",
            f"config:buy_rsi_range={config.buy_rsi_range[0]}..{config.buy_rsi_range[1]}",
            f"config:sell_rsi_range={config.sell_rsi_range[0]}..{config.sell_rsi_range[1]}",
        )
    return (*common, *specific)
