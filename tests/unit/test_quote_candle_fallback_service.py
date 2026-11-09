from datetime import UTC, datetime

from trading_ig_assistant.domain.market_data import Quote
from trading_ig_assistant.services.quote_candle_fallback_service import (
    QuoteCandleFallbackService,
)


def test_quote_candle_fallback_accumulates_m1_ohlc_for_each_side() -> None:
    service = QuoteCandleFallbackService()

    first = service.update(
        Quote(epic="BARRIER", bid=100.0, offer=102.0),
        observed_at_utc=datetime(2026, 11, 6, 12, 1, 5, tzinfo=UTC),
    )
    second = service.update(
        Quote(epic="BARRIER", bid=104.0, offer=106.0),
        observed_at_utc=datetime(2026, 11, 6, 12, 1, 30, tzinfo=UTC),
    )
    final = service.update(
        Quote(epic="BARRIER", bid=98.0, offer=100.0),
        observed_at_utc=datetime(2026, 11, 6, 12, 1, 59, tzinfo=UTC),
    )

    assert first is not None
    assert second is not None
    assert final is not None
    expected_minute_ms = int(datetime(2026, 11, 6, 12, 1, tzinfo=UTC).timestamp() * 1000)
    assert final.timestamp_ms == expected_minute_ms
    assert final.open == 101.0
    assert final.high == 105.0
    assert final.low == 99.0
    assert final.close == 99.0
    assert final.raw == {
        "LOCAL_QUOTE_CANDLE": 1.0,
        "BID_OPEN": 100.0,
        "BID_HIGH": 104.0,
        "BID_LOW": 98.0,
        "BID_CLOSE": 98.0,
        "OFR_OPEN": 102.0,
        "OFR_HIGH": 106.0,
        "OFR_LOW": 100.0,
        "OFR_CLOSE": 100.0,
        "MID_OPEN": 101.0,
        "MID_HIGH": 105.0,
        "MID_LOW": 99.0,
        "MID_CLOSE": 99.0,
    }


def test_mid_extremes_use_observed_midpoints_not_independent_side_extremes() -> None:
    from trading_ig_assistant.domain.market_data import ChartPriceBasis
    from trading_ig_assistant.services.candle_aggregation_service import chart_update_ohlc

    service = QuoteCandleFallbackService()
    observed = datetime(2026, 11, 6, 12, 1, tzinfo=UTC)
    service.update(Quote(epic="BARRIER", bid=100, offer=110), observed_at_utc=observed)
    update = service.update(Quote(epic="BARRIER", bid=104, offer=106), observed_at_utc=observed)
    assert update is not None
    assert chart_update_ohlc(update, ChartPriceBasis.MID) == (105, 105, 105, 105)
    assert chart_update_ohlc(update, ChartPriceBasis.BID) == (100, 104, 100, 104)


def test_older_quote_cannot_overwrite_prior_or_current_minute() -> None:
    service = QuoteCandleFallbackService()
    first = datetime(2026, 11, 6, 12, 1, 30, tzinfo=UTC)
    second = datetime(2026, 11, 6, 12, 2, 10, tzinfo=UTC)
    service.update(Quote(epic="BARRIER", bid=100, offer=102), observed_at_utc=first)
    assert service.update(Quote(epic="BARRIER", bid=110, offer=112), observed_at_utc=second)
    assert service.update(Quote(epic="BARRIER", bid=10, offer=12), observed_at_utc=first) is None
    update = service.update(Quote(epic="BARRIER", bid=112, offer=114), observed_at_utc=second)
    assert update is not None
    assert (update.open, update.high, update.low, update.close) == (111, 113, 111, 113)


def test_quote_candles_are_isolated_by_environment_and_account() -> None:
    service = QuoteCandleFallbackService()
    now = datetime(2026, 11, 6, 12, 1, tzinfo=UTC)
    quote = Quote(epic="BARRIER", bid=100, offer=102)
    service.update(quote, observed_at_utc=now, environment="live", account_id="A")
    different = Quote(epic="BARRIER", bid=200, offer=202)
    other_account = service.update(
        different, observed_at_utc=now, environment="live", account_id="B"
    )
    demo = service.update(different, observed_at_utc=now, environment="demo", account_id="A")
    original = service.update(quote, observed_at_utc=now, environment="live", account_id="A")
    assert other_account is not None and other_account.open == 201
    assert demo is not None and demo.open == 201
    assert original is not None and original.open == 101 and original.high == 101


def test_quote_candle_fallback_rolls_to_a_new_minute() -> None:
    service = QuoteCandleFallbackService()
    service.update(
        Quote(epic="BARRIER", bid=100.0, offer=102.0),
        observed_at_utc=datetime(2026, 11, 6, 12, 1, 59, tzinfo=UTC),
    )

    update = service.update(
        Quote(epic="BARRIER", bid=110.0, offer=112.0),
        observed_at_utc=datetime(2026, 11, 6, 12, 2, 1, tzinfo=UTC),
    )

    assert update is not None
    assert update.open == 111.0
    assert update.high == 111.0
    assert update.low == 111.0
    assert update.close == 111.0


def test_quote_candle_fallback_rejects_time_of_day_as_epoch_timestamp() -> None:
    service = QuoteCandleFallbackService()
    observed = datetime(2026, 11, 6, 12, 3, 15, tzinfo=UTC)

    update = service.update(
        Quote(epic="BARRIER", bid=100.0, offer=102.0, timestamp_ms=43_395_000),
        observed_at_utc=observed,
    )

    assert update is not None
    assert update.timestamp_ms == int(datetime(2026, 11, 6, 12, 3, tzinfo=UTC).timestamp() * 1000)
