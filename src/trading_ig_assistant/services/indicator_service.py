"""Deterministic indicators computed from closed, ordered candles."""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal

from trading_ig_assistant.domain.analysis import (
    DataState,
    IndicatorInput,
    IndicatorSeriesPoint,
    IndicatorSeriesSetValue,
    IndicatorSeriesValue,
    IndicatorSetValue,
    IndicatorValue,
)


def _result(
    indicator_input: IndicatorInput,
    name: str,
    required_points: int,
    *,
    period: int | None = None,
    state: DataState,
    value: Decimal | None = None,
    reason_codes: tuple[str, ...] = (),
) -> IndicatorValue:
    return IndicatorValue(
        name=name,
        state=state,
        value=value,
        required_points=required_points,
        observed_points=len(indicator_input.candles),
        reason_codes=reason_codes,
        provenance=indicator_input.provenance()
        + (f"indicator:{name}", f"period:{period or required_points}"),
    )


def _set_result(
    indicator_input: IndicatorInput,
    name: str,
    required_points: int,
    *,
    parameters: tuple[str, ...],
    state: DataState,
    values: tuple[tuple[str, Decimal], ...] = (),
    reason_codes: tuple[str, ...] = (),
) -> IndicatorSetValue:
    return IndicatorSetValue(
        name=name,
        state=state,
        values=values,
        required_points=required_points,
        observed_points=len(indicator_input.candles),
        reason_codes=reason_codes,
        provenance=indicator_input.provenance() + (f"indicator:{name}", *parameters),
    )


def _set_from_issue(
    indicator_input: IndicatorInput,
    name: str,
    issue: IndicatorValue,
    *,
    parameters: tuple[str, ...],
) -> IndicatorSetValue:
    return _set_result(
        indicator_input,
        name,
        issue.required_points,
        parameters=parameters,
        state=issue.state,
        reason_codes=issue.reason_codes,
    )


def _validate(
    indicator_input: IndicatorInput,
    name: str,
    period: int,
    required_points: int | None = None,
) -> IndicatorValue | None:
    if period <= 0:
        raise ValueError("indicator period must be positive")
    candles = indicator_input.candles
    for candle in candles:
        if candle.timestamp_utc.tzinfo is None or candle.timestamp_utc.utcoffset() != UTC.utcoffset(
            candle.timestamp_utc
        ):
            return _result(
                indicator_input,
                name,
                required_points or period,
                period=period,
                state=DataState.INVALID,
                reason_codes=("NON_UTC_TIMESTAMP",),
            )
        if not candle.closed:
            return _result(
                indicator_input,
                name,
                required_points or period,
                period=period,
                state=DataState.INVALID,
                reason_codes=("UNCLOSED_CANDLE",),
            )
        if candle.high < max(candle.open, candle.close) or candle.low > min(
            candle.open, candle.close
        ):
            return _result(
                indicator_input,
                name,
                required_points or period,
                period=period,
                state=DataState.INVALID,
                reason_codes=("INVALID_OHLC",),
            )
    if any(
        current.timestamp_utc <= previous.timestamp_utc
        for previous, current in zip(candles, candles[1:], strict=False)
    ):
        return _result(
            indicator_input,
            name,
            required_points or period,
            period=period,
            state=DataState.INVALID,
            reason_codes=("NON_INCREASING_TIMESTAMPS",),
        )
    needed = required_points or period
    if len(candles) < needed:
        return _result(
            indicator_input,
            name,
            needed,
            period=period,
            state=DataState.WARMING_UP,
            reason_codes=("INSUFFICIENT_HISTORY",),
        )
    return None


def sma(indicator_input: IndicatorInput, period: int) -> IndicatorValue:
    """Return the simple moving average over the latest ``period`` closes."""
    name = "sma"
    issue = _validate(indicator_input, name, period)
    if issue:
        return issue
    closes = [candle.close for candle in indicator_input.candles[-period:]]
    return _result(
        indicator_input,
        name,
        period,
        state=DataState.READY,
        value=sum(closes, Decimal("0")) / Decimal(period),
    )


def ema(indicator_input: IndicatorInput, period: int) -> IndicatorValue:
    """Return an EMA seeded by the first complete-period SMA."""
    name = "ema"
    issue = _validate(indicator_input, name, period)
    if issue:
        return issue
    closes = [candle.close for candle in indicator_input.candles]
    current = sum(closes[:period], Decimal("0")) / Decimal(period)
    alpha = Decimal("2") / Decimal(period + 1)
    for close in closes[period:]:
        current = ((close - current) * alpha) + current
    return _result(indicator_input, name, period, state=DataState.READY, value=current)


def ema_series(indicator_input: IndicatorInput, period: int) -> IndicatorSeriesValue:
    """Return every attested EMA point, aligned to its closed source candle."""

    name = "ema"
    issue = _validate(indicator_input, name, period)
    provenance = indicator_input.provenance() + (f"indicator:{name}", f"period:{period}")
    if issue is not None:
        return IndicatorSeriesValue(
            name=name,
            state=issue.state,
            points=(),
            required_points=issue.required_points,
            observed_points=issue.observed_points,
            reason_codes=issue.reason_codes,
            provenance=provenance,
        )
    values = _ema_series_values(
        [candle.close for candle in indicator_input.candles],
        period,
    )
    points = tuple(
        IndicatorSeriesPoint(
            timestamp_utc=indicator_input.candles[period - 1 + index].timestamp_utc,
            value=value,
        )
        for index, value in enumerate(values)
    )
    return IndicatorSeriesValue(
        name=name,
        state=DataState.READY,
        points=points,
        required_points=period,
        observed_points=len(indicator_input.candles),
        reason_codes=(),
        provenance=provenance,
    )


def rsi(indicator_input: IndicatorInput, period: int) -> IndicatorValue:
    """Return Wilder RSI, including explicit zero-gain/loss edge cases."""
    name = "rsi"
    required = period + 1
    issue = _validate(indicator_input, name, period, required)
    if issue:
        return issue
    closes = [candle.close for candle in indicator_input.candles]
    changes = [current - previous for previous, current in zip(closes, closes[1:], strict=False)]
    gains = [max(change, Decimal("0")) for change in changes]
    losses = [max(-change, Decimal("0")) for change in changes]
    average_gain = sum(gains[:period], Decimal("0")) / Decimal(period)
    average_loss = sum(losses[:period], Decimal("0")) / Decimal(period)
    for gain, loss in zip(gains[period:], losses[period:], strict=False):
        average_gain = ((average_gain * Decimal(period - 1)) + gain) / Decimal(period)
        average_loss = ((average_loss * Decimal(period - 1)) + loss) / Decimal(period)
    value = _rsi_value(average_gain, average_loss)
    return _result(
        indicator_input,
        name,
        required,
        period=period,
        state=DataState.READY,
        value=value,
    )


def rsi_series(indicator_input: IndicatorInput, period: int) -> IndicatorSeriesValue:
    """Return Wilder RSI points aligned to their closed source candles."""

    name = "rsi"
    required = period + 1
    issue = _validate(indicator_input, name, period, required)
    provenance = indicator_input.provenance() + (f"indicator:{name}", f"period:{period}")
    if issue is not None:
        return IndicatorSeriesValue(
            name=name,
            state=issue.state,
            points=(),
            required_points=issue.required_points,
            observed_points=issue.observed_points,
            reason_codes=issue.reason_codes,
            provenance=provenance,
        )
    closes = [candle.close for candle in indicator_input.candles]
    changes = [current - previous for previous, current in zip(closes, closes[1:], strict=False)]
    gains = [max(change, Decimal("0")) for change in changes]
    losses = [max(-change, Decimal("0")) for change in changes]
    average_gain = sum(gains[:period], Decimal("0")) / Decimal(period)
    average_loss = sum(losses[:period], Decimal("0")) / Decimal(period)
    values = [_rsi_value(average_gain, average_loss)]
    for gain, loss in zip(gains[period:], losses[period:], strict=False):
        average_gain = ((average_gain * Decimal(period - 1)) + gain) / Decimal(period)
        average_loss = ((average_loss * Decimal(period - 1)) + loss) / Decimal(period)
        values.append(_rsi_value(average_gain, average_loss))
    points = tuple(
        IndicatorSeriesPoint(
            timestamp_utc=indicator_input.candles[period + index].timestamp_utc,
            value=value,
        )
        for index, value in enumerate(values)
    )
    return IndicatorSeriesValue(
        name=name,
        state=DataState.READY,
        points=points,
        required_points=required,
        observed_points=len(indicator_input.candles),
        reason_codes=(),
        provenance=provenance,
    )


def atr(indicator_input: IndicatorInput, period: int) -> IndicatorValue:
    """Return Wilder ATR using high-low for the first true range."""
    name = "atr"
    issue = _validate(indicator_input, name, period)
    if issue:
        return issue
    candles = indicator_input.candles
    true_ranges = [candles[0].high - candles[0].low]
    for previous, current in zip(candles, candles[1:], strict=False):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    current_atr = sum(true_ranges[:period], Decimal("0")) / Decimal(period)
    for true_range in true_ranges[period:]:
        current_atr = ((current_atr * Decimal(period - 1)) + true_range) / Decimal(period)
    return _result(indicator_input, name, period, state=DataState.READY, value=current_atr)


def atr_series(indicator_input: IndicatorInput, period: int) -> IndicatorSeriesValue:
    """Return Wilder ATR points aligned to their closed source candles."""

    name = "atr"
    issue = _validate(indicator_input, name, period)
    provenance = indicator_input.provenance() + (f"indicator:{name}", f"period:{period}")
    if issue is not None:
        return IndicatorSeriesValue(
            name=name,
            state=issue.state,
            points=(),
            required_points=issue.required_points,
            observed_points=issue.observed_points,
            reason_codes=issue.reason_codes,
            provenance=provenance,
        )
    candles = indicator_input.candles
    true_ranges = [candles[0].high - candles[0].low]
    for previous, current in zip(candles, candles[1:], strict=False):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    current_atr = sum(true_ranges[:period], Decimal("0")) / Decimal(period)
    values = [current_atr]
    for true_range in true_ranges[period:]:
        current_atr = ((current_atr * Decimal(period - 1)) + true_range) / Decimal(period)
        values.append(current_atr)
    points = tuple(
        IndicatorSeriesPoint(
            timestamp_utc=indicator_input.candles[period - 1 + index].timestamp_utc,
            value=value,
        )
        for index, value in enumerate(values)
    )
    return IndicatorSeriesValue(
        name=name,
        state=DataState.READY,
        points=points,
        required_points=period,
        observed_points=len(indicator_input.candles),
        reason_codes=(),
        provenance=provenance,
    )


def macd_series(
    indicator_input: IndicatorInput,
    *,
    fast_period: int,
    slow_period: int,
    signal_period: int,
) -> IndicatorSeriesSetValue:
    """Return timestamped MACD, signal and histogram curves using EMA seeds."""

    if fast_period <= 0 or slow_period <= 0 or signal_period <= 0:
        raise ValueError("MACD periods must be positive")
    if fast_period >= slow_period:
        raise ValueError("MACD fast period must be lower than slow period")
    name = "macd"
    required = slow_period + signal_period - 1
    parameters = (
        f"fast_period:{fast_period}",
        f"slow_period:{slow_period}",
        f"signal_period:{signal_period}",
    )
    issue = _validate(indicator_input, name, slow_period, required)
    if issue:
        return IndicatorSeriesSetValue(
            name=name,
            state=issue.state,
            series=(),
            required_points=required,
            observed_points=len(indicator_input.candles),
            reason_codes=issue.reason_codes,
            provenance=indicator_input.provenance()
            + (f"indicator:{name}", *parameters),
        )
    closes = [candle.close for candle in indicator_input.candles]
    fast_values = _ema_series_values(closes, fast_period)
    slow_values = _ema_series_values(closes, slow_period)
    aligned_fast = fast_values[slow_period - fast_period :]
    line_values = [
        fast - slow for fast, slow in zip(aligned_fast, slow_values, strict=True)
    ]
    signal_values = _ema_series_values(line_values, signal_period)
    aligned_line_values = line_values[signal_period - 1 :]
    histogram_values = [
        line - signal
        for line, signal in zip(aligned_line_values, signal_values, strict=True)
    ]
    line_timestamps = indicator_input.candles[slow_period - 1 :]
    signal_timestamps = indicator_input.candles[required - 1 :]
    provenance = indicator_input.provenance() + (f"indicator:{name}", *parameters)
    component_values = (
        ("line", line_values, line_timestamps),
        ("signal", signal_values, signal_timestamps),
        ("histogram", histogram_values, signal_timestamps),
    )
    series = tuple(
        IndicatorSeriesValue(
            name=component,
            state=DataState.READY,
            points=tuple(
                IndicatorSeriesPoint(timestamp_utc=candle.timestamp_utc, value=value)
                for candle, value in zip(timestamps, values, strict=True)
            ),
            required_points=required,
            observed_points=len(indicator_input.candles),
            reason_codes=(),
            provenance=provenance + (f"component:{component}",),
        )
        for component, values, timestamps in component_values
    )
    return IndicatorSeriesSetValue(
        name=name,
        state=DataState.READY,
        series=series,
        required_points=required,
        observed_points=len(indicator_input.candles),
        reason_codes=(),
        provenance=provenance,
    )


def macd(
    indicator_input: IndicatorInput,
    *,
    fast_period: int,
    slow_period: int,
    signal_period: int,
) -> IndicatorSetValue:
    """Return the latest MACD line, signal line and histogram values."""

    series_result = macd_series(
        indicator_input,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
    )
    parameters = (
        f"fast_period:{fast_period}",
        f"slow_period:{slow_period}",
        f"signal_period:{signal_period}",
    )
    if series_result.state is not DataState.READY:
        return _set_result(
            indicator_input,
            "macd",
            series_result.required_points,
            parameters=parameters,
            state=series_result.state,
            reason_codes=series_result.reason_codes,
        )
    return _set_result(
        indicator_input,
        "macd",
        series_result.required_points,
        parameters=parameters,
        state=DataState.READY,
        values=tuple((item.name, item.points[-1].value) for item in series_result.series),
    )


def bollinger_bands(
    indicator_input: IndicatorInput,
    *,
    period: int,
    standard_deviations: Decimal,
) -> IndicatorSetValue:
    """Return population-standard-deviation Bollinger lower/middle/upper bands."""
    if standard_deviations <= 0:
        raise ValueError("Bollinger standard-deviation multiplier must be positive")
    name = "bollinger"
    parameters = (
        f"period:{period}",
        f"standard_deviations:{standard_deviations}",
        "deviation:population",
    )
    issue = _validate(indicator_input, name, period)
    if issue:
        return _set_from_issue(indicator_input, name, issue, parameters=parameters)
    closes = [candle.close for candle in indicator_input.candles[-period:]]
    middle = sum(closes, Decimal("0")) / Decimal(period)
    deviation = _population_standard_deviation(closes)
    distance = deviation * standard_deviations
    return _set_result(
        indicator_input,
        name,
        period,
        parameters=parameters,
        state=DataState.READY,
        values=(("lower", middle - distance), ("middle", middle), ("upper", middle + distance)),
    )


def momentum(indicator_input: IndicatorInput, period: int) -> IndicatorValue:
    """Return latest close minus the close ``period`` bars earlier."""
    name = "momentum"
    required = period + 1
    issue = _validate(indicator_input, name, period, required)
    if issue:
        return issue
    closes = [candle.close for candle in indicator_input.candles]
    return _result(
        indicator_input,
        name,
        required,
        period=period,
        state=DataState.READY,
        value=closes[-1] - closes[-required],
    )


def rate_of_change(indicator_input: IndicatorInput, period: int) -> IndicatorValue:
    """Return percentage rate of change over ``period`` closed bars."""
    name = "roc"
    required = period + 1
    issue = _validate(indicator_input, name, period, required)
    if issue:
        return issue
    closes = [candle.close for candle in indicator_input.candles]
    base = closes[-required]
    if base == 0:
        return _result(
            indicator_input,
            name,
            required,
            period=period,
            state=DataState.INVALID,
            reason_codes=("ZERO_BASE_PRICE",),
        )
    value = ((closes[-1] / base) - Decimal("1")) * Decimal("100")
    return _result(
        indicator_input,
        name,
        required,
        period=period,
        state=DataState.READY,
        value=value,
    )


def recent_levels(indicator_input: IndicatorInput, period: int) -> IndicatorSetValue:
    """Return the lowest low and highest high over the latest closed window."""
    name = "recent_levels"
    parameters = (f"period:{period}",)
    issue = _validate(indicator_input, name, period)
    if issue:
        return _set_from_issue(indicator_input, name, issue, parameters=parameters)
    candles = indicator_input.candles[-period:]
    return _set_result(
        indicator_input,
        name,
        period,
        parameters=parameters,
        state=DataState.READY,
        values=(
            ("support", min(candle.low for candle in candles)),
            ("resistance", max(candle.high for candle in candles)),
        ),
    )


def realized_volatility(
    indicator_input: IndicatorInput,
    *,
    period: int,
    annualization_periods: int,
) -> IndicatorValue:
    """Return annualized population volatility of arithmetic close-to-close returns in percent."""
    if annualization_periods <= 0:
        raise ValueError("volatility annualization periods must be positive")
    name = "realized_volatility"
    required = period + 1
    issue = _validate(indicator_input, name, period, required)
    if issue:
        return issue
    closes = [candle.close for candle in indicator_input.candles[-required:]]
    if any(close == 0 for close in closes[:-1]):
        return _result(
            indicator_input,
            name,
            required,
            period=period,
            state=DataState.INVALID,
            reason_codes=("ZERO_BASE_PRICE",),
        )
    returns = [
        (current / previous) - Decimal("1")
        for previous, current in zip(closes, closes[1:], strict=False)
    ]
    volatility = _population_standard_deviation(returns)
    annualized = volatility * Decimal(annualization_periods).sqrt() * Decimal("100")
    return IndicatorValue(
        name=name,
        state=DataState.READY,
        value=annualized,
        required_points=required,
        observed_points=len(indicator_input.candles),
        reason_codes=(),
        provenance=indicator_input.provenance()
        + (
            f"indicator:{name}",
            f"period:{period}",
            f"annualization_periods:{annualization_periods}",
            "returns:arithmetic",
            "deviation:population",
        ),
    )


def volume_ratio(indicator_input: IndicatorInput, period: int) -> IndicatorValue:
    """Return latest supplied volume divided by the prior-window average."""
    name = "volume_ratio"
    required = period + 1
    issue = _validate(indicator_input, name, period, required)
    if issue:
        return issue
    candles = indicator_input.candles[-required:]
    if any(candle.volume is None for candle in candles):
        return _result(
            indicator_input,
            name,
            required,
            period=period,
            state=DataState.INVALID,
            reason_codes=("MISSING_VOLUME",),
        )
    volumes = [candle.volume for candle in candles]
    prior_average = sum(
        (value for value in volumes[:-1] if value is not None), Decimal("0")
    ) / Decimal(period)
    if prior_average == 0:
        return _result(
            indicator_input,
            name,
            required,
            period=period,
            state=DataState.INVALID,
            reason_codes=("ZERO_VOLUME_BASE",),
        )
    latest = volumes[-1]
    assert latest is not None
    return _result(
        indicator_input,
        name,
        required,
        period=period,
        state=DataState.READY,
        value=latest / prior_average,
    )


def _ema_series_values(values: list[Decimal], period: int) -> list[Decimal]:
    current = sum(values[:period], Decimal("0")) / Decimal(period)
    result = [current]
    alpha = Decimal("2") / Decimal(period + 1)
    for value in values[period:]:
        current = ((value - current) * alpha) + current
        result.append(current)
    return result


def _rsi_value(average_gain: Decimal, average_loss: Decimal) -> Decimal:
    if average_gain == 0 and average_loss == 0:
        return Decimal("50")
    if average_loss == 0:
        return Decimal("100")
    if average_gain == 0:
        return Decimal("0")
    relative_strength = average_gain / average_loss
    return Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))


def _population_standard_deviation(values: list[Decimal]) -> Decimal:
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum(((value - mean) ** 2 for value in values), Decimal("0")) / Decimal(len(values))
    return variance.sqrt()


class IndicatorService:
    """Small facade for callers that prefer an injected service."""

    sma = staticmethod(sma)
    ema = staticmethod(ema)
    ema_series = staticmethod(ema_series)
    rsi = staticmethod(rsi)
    rsi_series = staticmethod(rsi_series)
    atr = staticmethod(atr)
    atr_series = staticmethod(atr_series)
    macd = staticmethod(macd)
    macd_series = staticmethod(macd_series)
    bollinger_bands = staticmethod(bollinger_bands)
    momentum = staticmethod(momentum)
    rate_of_change = staticmethod(rate_of_change)
    recent_levels = staticmethod(recent_levels)
    realized_volatility = staticmethod(realized_volatility)
    volume_ratio = staticmethod(volume_ratio)
