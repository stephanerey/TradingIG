from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.analysis import (
    AnalysisCandle,
    DataState,
    IndicatorInput,
    SignalSide,
)
from trading_ig_assistant.domain.replay import (
    ReplayDataset,
    ReplayExperimentConfig,
    ReplayPricePrecision,
)
from trading_ig_assistant.services.replay_strategy_service import run_strategy_replay
from trading_ig_assistant.services.technical_strategy_service import (
    BreakoutConfig,
    BreakoutStrategy,
    LevelParameters,
    PullbackConfig,
    PullbackStrategy,
    TrendFollowConfig,
    TrendFollowStrategy,
)

START = datetime(2026, 11, 5, 9, 0, tzinfo=UTC)
LEVELS = LevelParameters(
    entry_zone_atr=Decimal("0.1"),
    stop_atr=Decimal("1"),
    target_atr=Decimal("2"),
)


def _input(
    closes: tuple[str | int, ...],
    *,
    volumes: tuple[int | None, ...] | None = None,
    closed: bool = True,
) -> IndicatorInput:
    candles = []
    for index, raw_close in enumerate(closes):
        close = Decimal(raw_close)
        volume = None if volumes is None or volumes[index] is None else Decimal(volumes[index])
        candles.append(
            AnalysisCandle(
                timestamp_utc=START + timedelta(minutes=index),
                open=close,
                high=close + Decimal("0.5"),
                low=close - Decimal("0.5"),
                close=close,
                volume=volume,
                closed=closed,
            )
        )
    return IndicatorInput(
        instrument_id="SYNTHETIC",
        timeframe="M1",
        source="fixture",
        price_basis="mid",
        candles=tuple(candles),
    )


def _trend_config(*, max_extension: str = "2") -> TrendFollowConfig:
    return TrendFollowConfig(
        strategy_version="trend-v1",
        fast_ema_period=2,
        slow_ema_period=4,
        slope_lookback=2,
        atr_period=3,
        max_extension_atr=Decimal(max_extension),
        levels=LEVELS,
        valid_for=timedelta(minutes=5),
    )


def _breakout_config(*, minimum_volume_ratio: str | None = "1.5") -> BreakoutConfig:
    return BreakoutConfig(
        strategy_version="breakout-v1",
        level_lookback=3,
        atr_period=3,
        minimum_breakout_atr=Decimal("0.5"),
        maximum_extension_atr=Decimal("2"),
        maximum_atr_percent=Decimal("50"),
        volume_period=2 if minimum_volume_ratio is not None else None,
        minimum_volume_ratio=(
            Decimal(minimum_volume_ratio) if minimum_volume_ratio is not None else None
        ),
        levels=LEVELS,
        valid_for=timedelta(minutes=5),
    )


def _pullback_config(*, maximum_distance: str = "2") -> PullbackConfig:
    return PullbackConfig(
        strategy_version="pullback-v1",
        fast_ema_period=2,
        slow_ema_period=4,
        rsi_period=3,
        atr_period=3,
        maximum_distance_atr=Decimal(maximum_distance),
        buy_rsi_range=(Decimal("0"), Decimal("100")),
        sell_rsi_range=(Decimal("0"), Decimal("100")),
        levels=LEVELS,
        valid_for=timedelta(minutes=5),
    )


@pytest.mark.parametrize(
    ("closes", "expected_side"),
    (
        ((1, 2, 3, 4, 5, 6, 7, 8), SignalSide.BUY),
        ((8, 7, 6, 5, 4, 3, 2, 1), SignalSide.SELL),
    ),
)
def test_trend_follow_emits_directional_signal_with_auditable_levels(closes, expected_side) -> None:
    signal = TrendFollowStrategy(_trend_config()).evaluate(_input(closes))

    assert signal.side is expected_side
    assert signal.data_state is DataState.READY
    assert signal.reason_codes == ("TREND_CONFIRMED",)
    assert signal.entry_zone is not None
    assert signal.invalidation is not None
    assert signal.target is not None
    assert signal.generated_at_utc == START + timedelta(minutes=len(closes))
    assert "strategy:trend_follow" in signal.provenance
    assert "config:max_extension_atr=2" in signal.provenance


def test_trend_follow_rejects_extension_and_preserves_warmup() -> None:
    extended = TrendFollowStrategy(_trend_config(max_extension="0.01")).evaluate(
        _input((1, 2, 3, 4, 5, 6, 7, 8))
    )
    warming = TrendFollowStrategy(_trend_config()).evaluate(_input((1, 2, 3)))

    assert extended.side is SignalSide.FLAT
    assert extended.reason_codes == ("SIGNAL_TOO_EXTENDED",)
    assert warming.side is SignalSide.FLAT
    assert warming.data_state is DataState.WARMING_UP
    assert "INSUFFICIENT_HISTORY" in warming.reason_codes


@pytest.mark.parametrize(
    ("last_close", "expected_side"),
    (("12", SignalSide.BUY), ("8", SignalSide.SELL)),
)
def test_breakout_uses_prior_levels_atr_and_volume(last_close, expected_side) -> None:
    signal = BreakoutStrategy(_breakout_config()).evaluate(
        _input((10, 10, 10, last_close), volumes=(10, 10, 10, 20))
    )

    assert signal.side is expected_side
    assert signal.reason_codes == ("BREAKOUT_CONFIRMED",)
    assert dict(signal.features)["volume_ratio"] == Decimal("2")
    assert signal.data_quality == Decimal("1")


def test_breakout_rejects_missing_or_weak_volume_confirmation() -> None:
    missing = BreakoutStrategy(_breakout_config()).evaluate(_input((10, 10, 10, 12)))
    weak = BreakoutStrategy(_breakout_config()).evaluate(
        _input((10, 10, 10, 12), volumes=(10, 10, 10, 10))
    )

    assert missing.data_state is DataState.INVALID
    assert "MISSING_VOLUME" in missing.reason_codes
    assert weak.data_state is DataState.READY
    assert weak.side is SignalSide.FLAT
    assert weak.reason_codes == ("VOLUME_CONFIRMATION_FAILED",)


@pytest.mark.parametrize(
    ("closes", "expected_side"),
    (
        ((1, 2, 3, 4, 5, 6, "5.4", "5.8"), SignalSide.BUY),
        ((8, 7, 6, 5, 4, 3, "3.6", "3.2"), SignalSide.SELL),
    ),
)
def test_pullback_requires_trend_zone_and_price_confirmation(closes, expected_side) -> None:
    signal = PullbackStrategy(_pullback_config()).evaluate(_input(closes))

    assert signal.side is expected_side
    assert signal.reason_codes == ("PULLBACK_CONFIRMED",)
    assert "distance_from_fast_atr" in dict(signal.features)


def test_pullback_rejects_price_outside_configured_zone() -> None:
    signal = PullbackStrategy(_pullback_config(maximum_distance="0.01")).evaluate(
        _input((1, 2, 3, 4, 5, 6, "5.4", "5.8"))
    )

    assert signal.side is SignalSide.FLAT
    assert signal.reason_codes == ("NO_PULLBACK_ZONE",)


def test_unclosed_data_never_produces_actionable_signal() -> None:
    signal = TrendFollowStrategy(_trend_config()).evaluate(_input((1, 2, 3, 4, 5, 6), closed=False))

    assert signal.side is SignalSide.FLAT
    assert signal.data_state is DataState.INVALID
    assert "UNCLOSED_CANDLE" in signal.reason_codes


def test_concrete_strategy_runs_future_blind_in_replay() -> None:
    indicator_input = _input((1, 2, 3, 4, 5, 6, 7, 8))
    strategy = TrendFollowStrategy(_trend_config())
    dataset = ReplayDataset(
        dataset_id="TECHNICAL-FIXTURE",
        dataset_version="v1",
        instrument_id=indicator_input.instrument_id,
        timeframe=indicator_input.timeframe,
        source=indicator_input.source,
        price_basis=indicator_input.price_basis,
        resolution_seconds=60,
        candles=indicator_input.candles,
    )
    config = ReplayExperimentConfig(
        experiment_id="TREND-FOLLOW-FIXTURE",
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        strategy_id=strategy.strategy_id,
        rules_version="trend-v1",
        code_revision="fixture",
        management_mode="signal-only",
        currency="EUR",
        fill_model_version="paper-fill-v1",
        price_precision=ReplayPricePrecision.OHLC_APPROXIMATION,
    )

    evidence = run_strategy_replay(
        config,
        dataset,
        strategy,
        required_warmup_points=6,
    )

    assert [len(item.frame.indicator_input.candles) for item in evidence] == list(range(1, 9))
    assert all(item.signal.generated_at_utc == item.frame.latest_source_at_utc for item in evidence)
    assert evidence[-1].signal.side is SignalSide.BUY


def test_invalid_strategy_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="fast < slow"):
        TrendFollowConfig(
            strategy_version="v1",
            fast_ema_period=4,
            slow_ema_period=2,
            slope_lookback=1,
            atr_period=3,
            max_extension_atr=Decimal("1"),
            levels=LEVELS,
            valid_for=timedelta(minutes=1),
        )
    with pytest.raises(ValueError, match="configured together"):
        BreakoutConfig(
            strategy_version="v1",
            level_lookback=3,
            atr_period=3,
            minimum_breakout_atr=Decimal("0.5"),
            maximum_extension_atr=Decimal("2"),
            maximum_atr_percent=Decimal("10"),
            volume_period=2,
            minimum_volume_ratio=None,
            levels=LEVELS,
            valid_for=timedelta(minutes=1),
        )
