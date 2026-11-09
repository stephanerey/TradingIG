"""Explicit candle-close availability times for future-blind strategies."""

from __future__ import annotations

from datetime import timedelta

from trading_ig_assistant.domain.analysis import AnalysisCandle

_TIMEFRAME_DURATIONS = {
    "M1": timedelta(minutes=1),
    "1MINUTE": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "5MINUTE": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "15MINUTE": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "30MINUTE": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "1HOUR": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "4HOUR": timedelta(hours=4),
    "D1": timedelta(days=1),
    "1DAY": timedelta(days=1),
}


def timeframe_duration(timeframe: str) -> timedelta:
    normalized = timeframe.upper().replace(" ", "")
    try:
        return _TIMEFRAME_DURATIONS[normalized]
    except KeyError as exc:
        raise ValueError("strategy timeframe must have an explicit close duration") from exc


def candle_available_at(candle: AnalysisCandle, timeframe: str):
    return candle.timestamp_utc + timeframe_duration(timeframe)
