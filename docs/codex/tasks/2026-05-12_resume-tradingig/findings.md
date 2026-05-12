# Findings

Date: 2026-05-12

## Project State

- The repository is in the P02 streaming/chart foundation area, despite the branch name still being `codex/p01-product-discovery-gui`.
- The application is still read-only. REST order paths raise `LiveTradingDisabledError`.
- The README says live chart updates are limited to live quote header and live price line, but the code now has a fuller candle foundation with `CandleHistoryService` and stream candle persistence. README is behind the latest commits.

## Historical Candles

- `IGRestAdapter.get_prices` supports snapshot, date-range, date-range fallback to max-points, and max-points history requests.
- `load_prices_with_adaptive_fallback` tries requested max points and then lower values: `5000`, `3000`, `2000`, `1000`, `600`, `300`, `120`.
- `is_historical_allowance_error` matches the IG historical allowance error code.
- `MainWindow._load_selected_product_history` loads stream cache, then REST history cache, then REST fallback, and renders the first available source.
- REST history cache is saved by environment, hashed account marker, epic, resolution, range key, price basis, and max points.

## Streaming Candles

- `IGStreamingAdapter.subscribe_chart` subscribes to `CHART:{epic}:{scale}` with fields from `CHART_CANDLE_SPEC`.
- `MainWindow._restart_streaming` requests the chart scale derived from the UI interval.
- If a direct chart scale fails, `_on_stream_error` attempts a `1MINUTE` chart subscription fallback.
- `_on_stream_chart` sends `ChartCandleUpdate` into `CandleHistoryService.apply_stream_update`, then renders the canonical candles.

## Cache Candles

- Completed stream candles are appended as JSONL through `CandleHistoryService._persist_closed_candle`.
- Stream cache path includes environment, hashed account marker, chart-source epic, interval seconds, and price basis.
- Stream cache payload stores environment, chart source epic, interval, price basis, source, timestamp, OHLC, and volume. It does not store raw account id or credentials.
- REST cache payload stores saved timestamp, epic, resolution, range key, price basis, max points, and prices.

## IG REST

- The REST adapter logs redacted headers and response bodies.
- Login stores CST/XST only in memory.
- Account switching preserves refreshed tokens from response headers when present.
- Product discovery and chart-source targeted search use read-only REST calls.

## Lightstreamer

- Streaming uses Lightstreamer user `account_id` and password `CST-...|XST-...`.
- Quote subscriptions default to `PRICE:{account_id}:{epic}`.
- Chart subscriptions default to `CHART:{epic}:{scale}`.
- `stream-market` diagnostics can test default or custom templates.

## Chart UI

- `ChartView` defaults to 5-minute candles, 1M range, MID basis, and compressed axis.
- `ChartView.set_candles` renders canonical `Candle` values.
- `ChartView.set_live_quote` updates header labels and live price line using the currently selected price basis.
- `MainWindow` connects chart resolution and range changes to history reload.

## Confirmed Gap

Price-basis changes are not propagated from `ChartView` to `MainWindow`:

- `ChartView` has `resolution_changed` and `history_range_changed`, but no signal for price basis changes.
- `MainWindow` does not reload history when Bid/Mid/Ask changes.
- With the new canonical candle path, `set_candles` receives already-computed candle values, so `ChartView._on_price_basis_changed` cannot recompute REST/cache candles from raw bid/offer data.

## Uncertainties

- No real IG credentialed smoke test was run in this pass.
- It is unknown whether current live/demo account permissions still trigger historical allowance errors.
- It is unknown whether every target market accepts direct chart scales above `1MINUTE`.
- The recovery file contains mojibake and historical logs; it is useful for hints, not truth.
