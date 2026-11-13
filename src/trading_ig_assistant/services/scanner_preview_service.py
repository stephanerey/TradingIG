"""Manual analysis-only scanner preview over a conservatively closed chart prefix."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_ig_assistant.domain.analysis import (
    AnalysisCandle,
    IndicatorInput,
    IndicatorSetValue,
    IndicatorValue,
    StrategyConsensus,
    StrategyId,
    StrategySignal,
)
from trading_ig_assistant.domain.market_data import ChartCandleSeries
from trading_ig_assistant.services.indicator_service import (
    atr,
    ema,
    recent_levels,
    rsi,
    volume_ratio,
)
from trading_ig_assistant.services.setup_scoring_service import StrategyRegistry, build_consensus
from trading_ig_assistant.services.technical_strategy_service import (
    BreakoutConfig,
    BreakoutStrategy,
    LevelParameters,
    PullbackConfig,
    PullbackStrategy,
    TrendFollowConfig,
    TrendFollowStrategy,
)

PREVIEW_RULES_VERSION = "scanner-preview-v1-unvalidated"


@dataclass(frozen=True)
class ScannerPreview:
    instrument_id: str
    timeframe: str
    used_closed_candles: int
    excluded_trailing_candles: int
    excluded_pre_gap_candles: int
    signals: tuple[StrategySignal, ...]
    consensus: StrategyConsensus
    limitations: tuple[str, ...]
    indicators: tuple[IndicatorValue | IndicatorSetValue, ...] = ()


@dataclass(frozen=True)
class ScannerStrategyProfile:
    profile_id: str
    enabled_strategies: tuple[StrategyId, ...]
    trend_follow: TrendFollowConfig
    breakout: BreakoutConfig
    pullback: PullbackConfig

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("scanner strategy profile ID is required")
        if not self.enabled_strategies:
            raise ValueError("scanner strategy profile must enable at least one strategy")
        if any(not isinstance(strategy, StrategyId) for strategy in self.enabled_strategies):
            raise ValueError("scanner strategy profile contains an invalid strategy ID")
        if len(set(self.enabled_strategies)) != len(self.enabled_strategies):
            raise ValueError("scanner strategy profile contains duplicate strategies")


def build_scanner_preview(
    series: ChartCandleSeries,
    *,
    as_of_utc: datetime | None = None,
    strategy_profile: ScannerStrategyProfile | None = None,
) -> ScannerPreview:
    if as_of_utc is not None:
        _validate_series_freshness(series, as_of_utc=as_of_utc)
    indicator_input = chart_series_to_closed_indicator_input(series)
    excluded_trailing_candles = 1 if series.candles else 0
    closed_candle_count = len(series.candles) - excluded_trailing_candles
    excluded_pre_gap_candles = closed_candle_count - len(indicator_input.candles)
    profile = strategy_profile or default_scanner_strategy_profile()
    registry = _preview_registry(profile)
    signals = registry.evaluate(indicator_input)
    indicators = _profile_indicators(indicator_input, profile)
    return ScannerPreview(
        instrument_id=indicator_input.instrument_id,
        timeframe=indicator_input.timeframe,
        used_closed_candles=len(indicator_input.candles),
        excluded_trailing_candles=excluded_trailing_candles,
        excluded_pre_gap_candles=excluded_pre_gap_candles,
        signals=signals,
        consensus=build_consensus(signals),
        limitations=(
            "ANALYSIS_ONLY",
            "PREVIEW_PARAMETERS_NOT_VALIDATED_FOR_AUTO",
            "LAST_CHART_CANDLE_EXCLUDED_AS_POTENTIALLY_OPEN",
            "EVENT_DRIVEN_REQUIRES_QUALIFIED_CONTEXT",
            "NO_COMPLETE_SCANNER_SCORE",
            "NO_TICKET_OR_ORDER_PATH",
            f"STRATEGY_PROFILE:{profile.profile_id}",
            *(("DATA_GAP_EARLIER_CANDLES_EXCLUDED",) if excluded_pre_gap_candles else ()),
        ),
        indicators=indicators,
    )


def chart_series_to_closed_indicator_input(series: ChartCandleSeries) -> IndicatorInput:
    timeframe = _timeframe_from_seconds(series.resolution_seconds)
    sources = "+".join(sorted({source.value for source in series.sources})) or "UNKNOWN"
    closed_prefix = series.candles[:-1] if series.candles else ()
    continuous_suffix = _continuous_suffix(
        closed_prefix,
        interval=timedelta(seconds=series.resolution_seconds),
    )
    candles = tuple(
        AnalysisCandle(
            timestamp_utc=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            closed=True,
        )
        for candle in continuous_suffix
    )
    return IndicatorInput(
        instrument_id=series.selected_product_epic,
        timeframe=timeframe,
        source=f"chart:{sources}:trailing-candle-excluded:continuous-suffix-only",
        price_basis=series.price_basis.value,
        candles=candles,
    )


def _continuous_suffix(candles, *, interval: timedelta):
    if not candles:
        return candles
    start = len(candles) - 1
    while start > 0:
        previous = candles[start - 1]
        current = candles[start]
        if current.timestamp - previous.timestamp != interval:
            break
        start -= 1
    return candles[start:]


def _validate_series_freshness(
    series: ChartCandleSeries,
    *,
    as_of_utc: datetime,
) -> None:
    if as_of_utc.tzinfo is None:
        raise ValueError("scanner freshness reference must be timezone-aware")
    if not series.candles:
        raise ValueError("scanner preview requires chart candles")
    interval = timedelta(seconds=series.resolution_seconds)
    latest_timestamp = series.candles[-1].timestamp
    reference = as_of_utc.astimezone(UTC)
    if latest_timestamp > reference + interval:
        raise ValueError("chart history timestamp is in the future")
    # The latest item can be the currently open candle. Two additional periods are
    # tolerated for feed scheduling, but an old persisted snapshot must never drive
    # a scanner signal after an application restart or a prolonged interruption.
    if reference - (latest_timestamp + interval) > interval * 2:
        raise ValueError("STALE_HISTORY: refresh the selected timeframe before analysis")


def default_scanner_strategy_profile() -> ScannerStrategyProfile:
    levels = LevelParameters(
        entry_zone_atr=Decimal("0.10"),
        stop_atr=Decimal("1.00"),
        target_atr=Decimal("2.00"),
    )
    return ScannerStrategyProfile(
        profile_id=PREVIEW_RULES_VERSION,
        enabled_strategies=(
            StrategyId.TREND_FOLLOW,
            StrategyId.BREAKOUT,
            StrategyId.PULLBACK,
        ),
        trend_follow=TrendFollowConfig(
            strategy_version=PREVIEW_RULES_VERSION,
            fast_ema_period=9,
            slow_ema_period=21,
            slope_lookback=3,
            atr_period=14,
            max_extension_atr=Decimal("1.50"),
            levels=levels,
            valid_for=timedelta(minutes=5),
        ),
        breakout=BreakoutConfig(
            strategy_version=PREVIEW_RULES_VERSION,
            level_lookback=20,
            atr_period=14,
            minimum_breakout_atr=Decimal("0.25"),
            maximum_extension_atr=Decimal("2.50"),
            maximum_atr_percent=Decimal("5.00"),
            volume_period=None,
            minimum_volume_ratio=None,
            levels=levels,
            valid_for=timedelta(minutes=5),
        ),
        pullback=PullbackConfig(
            strategy_version=PREVIEW_RULES_VERSION,
            fast_ema_period=9,
            slow_ema_period=21,
            rsi_period=14,
            atr_period=14,
            maximum_distance_atr=Decimal("1.00"),
            buy_rsi_range=(Decimal("35"), Decimal("60")),
            sell_rsi_range=(Decimal("40"), Decimal("65")),
            levels=levels,
            valid_for=timedelta(minutes=5),
        ),
    )


def required_closed_candles(profile: ScannerStrategyProfile) -> int:
    """Return the closed, continuous history required by enabled strategies."""

    requirements: list[int] = []
    if StrategyId.TREND_FOLLOW in profile.enabled_strategies:
        config = profile.trend_follow
        requirements.append(
            max(config.slow_ema_period + config.slope_lookback, config.atr_period)
        )
    if StrategyId.BREAKOUT in profile.enabled_strategies:
        config = profile.breakout
        requirements.append(
            max(config.level_lookback + 1, config.atr_period, config.volume_period or 0)
        )
    if StrategyId.PULLBACK in profile.enabled_strategies:
        config = profile.pullback
        requirements.append(
            max(config.slow_ema_period, config.rsi_period + 1, config.atr_period, 2)
        )
    if not requirements:
        raise ValueError("scanner profile has no supported technical strategy")
    return max(requirements)


def _profile_indicators(
    indicator_input: IndicatorInput,
    profile: ScannerStrategyProfile,
) -> tuple[IndicatorValue | IndicatorSetValue, ...]:
    """Expose the exact deterministic indicators consumed by the active profile."""

    requested: list[tuple[str, int]] = []
    if StrategyId.TREND_FOLLOW in profile.enabled_strategies:
        config = profile.trend_follow
        requested.extend(
            (
                ("ema", config.fast_ema_period),
                ("ema", config.slow_ema_period),
                ("atr", config.atr_period),
            )
        )
    if StrategyId.BREAKOUT in profile.enabled_strategies:
        config = profile.breakout
        requested.extend(
            (
                ("recent_levels", config.level_lookback),
                ("atr", config.atr_period),
            )
        )
        if config.volume_period is not None:
            requested.append(("volume_ratio", config.volume_period))
    if StrategyId.PULLBACK in profile.enabled_strategies:
        config = profile.pullback
        requested.extend(
            (
                ("ema", config.fast_ema_period),
                ("ema", config.slow_ema_period),
                ("rsi", config.rsi_period),
                ("atr", config.atr_period),
            )
        )

    results: list[IndicatorValue | IndicatorSetValue] = []
    for name, period in dict.fromkeys(requested):
        if name == "ema":
            results.append(ema(indicator_input, period))
        elif name == "atr":
            results.append(atr(indicator_input, period))
        elif name == "rsi":
            results.append(rsi(indicator_input, period))
        elif name == "recent_levels":
            results.append(recent_levels(indicator_input, period))
        elif name == "volume_ratio":
            results.append(volume_ratio(indicator_input, period))
        else:  # pragma: no cover - guarded by the explicit profile mapping above.
            raise ValueError(f"unsupported scanner indicator: {name}")
    return tuple(results)


def _preview_registry(profile: ScannerStrategyProfile) -> StrategyRegistry:
    registry = StrategyRegistry()
    if StrategyId.TREND_FOLLOW in profile.enabled_strategies:
        registry.register(TrendFollowStrategy(profile.trend_follow))
    if StrategyId.BREAKOUT in profile.enabled_strategies:
        registry.register(BreakoutStrategy(profile.breakout))
    if StrategyId.PULLBACK in profile.enabled_strategies:
        registry.register(PullbackStrategy(profile.pullback))
    return registry


def _timeframe_from_seconds(seconds: int) -> str:
    try:
        return {
            60: "M1",
            300: "M5",
            900: "M15",
            1800: "M30",
            3600: "H1",
            14400: "H4",
            86400: "D1",
        }[seconds]
    except KeyError as exc:
        raise ValueError("scanner preview resolution is unsupported") from exc
