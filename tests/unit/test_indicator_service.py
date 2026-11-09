from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_ig_assistant.domain.analysis import AnalysisCandle, DataState, IndicatorInput
from trading_ig_assistant.services.indicator_service import (
    atr,
    bollinger_bands,
    ema,
    macd,
    momentum,
    rate_of_change,
    realized_volatility,
    recent_levels,
    rsi,
    sma,
    volume_ratio,
)


def _input(
    closes: tuple[int, ...],
    *,
    closed: bool = True,
    invalid_ohlc: bool = False,
    volumes: tuple[int | None, ...] | None = None,
) -> IndicatorInput:
    start = datetime(2026, 10, 22, 10, 0, tzinfo=UTC)
    candles = []
    for index, close_number in enumerate(closes):
        close = Decimal(close_number)
        candles.append(
            AnalysisCandle(
                timestamp_utc=start + timedelta(minutes=index),
                open=close,
                high=close - 1 if invalid_ohlc and index == 0 else close + 1,
                low=close - 1,
                close=close,
                volume=(
                    Decimal(volumes[index])
                    if volumes is not None and volumes[index] is not None
                    else None
                ),
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


def test_numeric_indicator_fixtures_are_deterministic() -> None:
    indicator_input = _input((1, 2, 3, 4, 5))

    assert sma(indicator_input, 3).value == Decimal("4")
    assert ema(indicator_input, 3).value == Decimal("4")
    assert rsi(indicator_input, 3).value == Decimal("100")
    assert atr(indicator_input, 3).value == Decimal("2")


def test_insufficient_history_is_warming_up_without_value() -> None:
    result = sma(_input((1, 2)), 3)

    assert result.state is DataState.WARMING_UP
    assert result.value is None
    assert result.reason_codes == ("INSUFFICIENT_HISTORY",)


def test_unclosed_candle_is_invalid() -> None:
    result = ema(_input((1, 2, 3), closed=False), 3)

    assert result.state is DataState.INVALID
    assert result.reason_codes == ("UNCLOSED_CANDLE",)


def test_invalid_ohlc_is_rejected() -> None:
    result = atr(_input((1, 2, 3), invalid_ohlc=True), 3)

    assert result.state is DataState.INVALID
    assert result.reason_codes == ("INVALID_OHLC",)


def test_non_increasing_timestamps_are_rejected() -> None:
    indicator_input = _input((1, 2, 3))
    duplicated = IndicatorInput(
        instrument_id=indicator_input.instrument_id,
        timeframe=indicator_input.timeframe,
        source=indicator_input.source,
        price_basis=indicator_input.price_basis,
        candles=(
            indicator_input.candles[0],
            indicator_input.candles[0],
            indicator_input.candles[2],
        ),
    )

    result = sma(duplicated, 3)

    assert result.state is DataState.INVALID
    assert result.reason_codes == ("NON_INCREASING_TIMESTAMPS",)


def test_rsi_reports_period_and_required_history_separately() -> None:
    result = rsi(_input((1, 2, 3, 4)), 3)

    assert result.required_points == 4
    assert "period:3" in result.provenance


def test_macd_fixture_returns_line_signal_and_histogram() -> None:
    result = macd(_input((1, 2, 3, 4, 5, 6)), fast_period=2, slow_period=3, signal_period=2)

    assert result.state is DataState.READY
    assert dict(result.values) == {
        "line": Decimal("0.5"),
        "signal": Decimal("0.5"),
        "histogram": Decimal("0.0"),
    }
    assert result.required_points == 4


def test_bollinger_fixture_uses_population_standard_deviation() -> None:
    result = bollinger_bands(
        _input((1, 2, 3, 4, 5)),
        period=5,
        standard_deviations=Decimal("2"),
    )
    values = dict(result.values)

    assert values["middle"] == Decimal("3")
    assert values["upper"].quantize(Decimal("0.000001")) == Decimal("5.828427")
    assert values["lower"].quantize(Decimal("0.000001")) == Decimal("0.171573")
    assert "deviation:population" in result.provenance


def test_momentum_roc_and_recent_levels_are_deterministic() -> None:
    indicator_input = _input((1, 2, 3, 4, 5))

    assert momentum(indicator_input, 3).value == Decimal("3")
    assert rate_of_change(indicator_input, 3).value == Decimal("150.0")
    assert dict(recent_levels(indicator_input, 3).values) == {
        "support": Decimal("2"),
        "resistance": Decimal("6"),
    }


def test_realized_volatility_requires_explicit_annualization() -> None:
    result = realized_volatility(
        _input((1, 2, 4, 8)),
        period=3,
        annualization_periods=252,
    )

    assert result.state is DataState.READY
    assert result.value == Decimal("0")
    assert "annualization_periods:252" in result.provenance


def test_volume_ratio_requires_supplied_nonzero_volume() -> None:
    ready = volume_ratio(_input((1, 2, 3), volumes=(10, 10, 20)), 2)
    missing = volume_ratio(_input((1, 2, 3)), 2)
    zero = volume_ratio(_input((1, 2, 3), volumes=(0, 0, 20)), 2)

    assert ready.value == Decimal("2")
    assert missing.state is DataState.INVALID
    assert missing.reason_codes == ("MISSING_VOLUME",)
    assert zero.state is DataState.INVALID
    assert zero.reason_codes == ("ZERO_VOLUME_BASE",)


def test_new_indicators_preserve_warmup_and_invalid_closed_data_rules() -> None:
    warming = macd(_input((1, 2, 3)), fast_period=2, slow_period=3, signal_period=2)
    invalid = bollinger_bands(
        _input((1, 2, 3), closed=False),
        period=3,
        standard_deviations=Decimal("2"),
    )

    assert warming.state is DataState.WARMING_UP
    assert warming.values == ()
    assert invalid.state is DataState.INVALID
    assert invalid.reason_codes == ("UNCLOSED_CANDLE",)


def test_invalid_indicator_parameters_are_rejected() -> None:
    indicator_input = _input((1, 2, 3, 4))

    for call in (
        lambda: macd(indicator_input, fast_period=3, slow_period=2, signal_period=2),
        lambda: bollinger_bands(
            indicator_input,
            period=3,
            standard_deviations=Decimal("0"),
        ),
        lambda: realized_volatility(
            indicator_input,
            period=3,
            annualization_periods=0,
        ),
    ):
        try:
            call()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid indicator parameters must be rejected")
