# P02 Streaming Diagnostics

## Purpose

Validate IG streaming subscriptions outside the PyQt GUI so market-data issues can be debugged
from the CLI first.

## Tested Environment

- Environment: pending manual run
- Branch: `codex/p01-product-discovery-gui`
- Command: `trading-ig-assistant stream-market`

## Tested EPICs

- Pending manual validation

## Subscription Templates Tried

- `MARKET:{epic}`
- `PRICE:{account_id}:{epic}`
- `CHART:{epic}:1MINUTE`
- Optional custom templates via `--try-price-template`

## Fields Received

### MARKET

- `BID`
- `OFFER`
- `UPDATE_TIME`
- `MARKET_STATE`
- `CHANGE`
- `CHANGE_PCT`

### PRICE

- `BIDPRICE1`
- `ASKPRICE1`
- `TIMESTAMP`
- `NET_CHG`
- `NET_CHG_PCT`
- other top-of-book fields when available

### CHART

- `UTM`
- `BID_OPEN`
- `BID_HIGH`
- `BID_LOW`
- `BID_CLOSE`
- `OFR_OPEN`
- `OFR_HIGH`
- `OFR_LOW`
- `OFR_CLOSE`
- `DAY_NET_CHG_MID`
- `DAY_PERC_CHG_MID`
- `CONS_END`

## Which Template Works

- Pending manual validation with real IG credentials.
- The CLI now reports explicit success/failure for each template independently.

## Observed Error Codes

- Pending manual validation
- Expected possibilities:
  - subscription item rejected
  - subscription limit exceeded
  - no first tick received during duration

## Remaining Unknowns

- Which quote template is most reliable for barrier and option products on the user account.
- Whether `MARKET:{epic}` is supported for the same EPICs as `PRICE:{account_id}:{epic}`.
- Whether some products stream only chart updates and not quote updates.
- Which subscriptions are account-permission dependent versus market-type dependent.

## Historical Backfill Fix

- The previous GUI backfill path used date-range REST requests.
- IG returned `error.malformed.date` on those historical `/prices/{epic}/{resolution}` calls.
- The GUI now uses max-points REST backfill by default:
  - `/prices/{epic}/{resolution}/{max_points}`
- Date-range mode remains available for diagnostics and can fall back automatically to max-points
  mode when IG returns `error.malformed.date`, `HTTP 400`, or an empty price list and
  `max_points` is available.
- Live streaming remains independent from history backfill:
  - if REST history fails, the live chart still runs
  - the GUI shows: `Historical backfill unavailable; live chart is running.`

## Chart History / Axis / Price Basis

- The chart timeframe now defaults to `5 Min` both visually and internally.
- The first history request for a newly selected product uses `MINUTE_5` immediately when the
  dropdown shows `5 Min`.
- A history range selector is available:
  - `1D`
  - `5D`
  - `1M`
  - `3M`
  - `6M`
  - `1Y`
  - `Max`
- The default history range is `1M`.
- History depth is calculated from `timeframe + range` and capped conservatively at `10,000`
  points for IG REST max-points requests.
- The default chart price basis is `MID`.
- Price basis can be switched between:
  - `Bid`
  - `Mid`
  - `Ask`
- The selected price basis is applied consistently to:
  - historical REST candle conversion
  - live `CHART` candle updates
  - the blue live price line
- The time axis now defaults to `Compressed`.
- In compressed mode:
  - candles are rendered on sequential X positions
  - weekend and market-closed gaps are hidden
  - original timestamps are still preserved for hover/crosshair display and future indicators
- A `Real` time-axis mode remains available as a fallback/debug display.

## Historical Data Allowance Handling

- IG may reject larger historical requests with:
  - `error.public-api.exceeded-account-historical-data-allowance`
- The GUI no longer fails immediately on the first large request.
- Historical backfill now uses an adaptive fallback ladder:
  - requested points
  - `5000`
  - `3000`
  - `2000`
  - `1000`
  - `600`
  - `300`
  - `120`
- Values larger than the originally requested `max_points` are skipped.
- The first successful non-empty response is used for display.
- As a result, the displayed history range may be shorter than requested when IG rejects larger
  historical requests.
- Logs now show:
  - requested points
  - attempted points
  - final selected points
  - loaded candle count
  - selected product epic
  - chart source epic
- If all historical fallback attempts fail because of historical allowance limits, the GUI shows:
  - `Historical backfill unavailable due to IG historical data allowance; live chart is running.`
- Live streaming remains independent from historical backfill:
  - the chart still receives live `CHART` updates
  - no live trading is implemented

## Historical Allowance Pause / Cached History / Chart Source

- Once IG reports `error.public-api.exceeded-account-historical-data-allowance`, the GUI
  finishes the current fallback ladder and then pauses further automatic historical REST retries
  for that account during the session.
- While paused, the GUI does not keep retrying on product refresh, timeframe change, or range
  change.
- The user-facing status becomes:
  - `IG historical data allowance reached; live chart continues. Retry later or use cached history.`
- Successful historical backfills are cached locally under:
  - `~/.trading_ig_assistant/cache/history/`
- Cached files contain only chart data and metadata:
  - environment
  - masked/hash account marker
  - epic
  - resolution
  - price basis
  - range/max points
  - saved timestamp
- No credentials, CST/XST tokens, API keys, or passwords are stored in history cache files.
- On later reloads, cached history is loaded first when available and the UI reports the cache
  timestamp being used.
- Chart source resolution now prefers an underlying cash/DFB market over the selected
  barrier/option EPIC when a matching underlying can be found.
- Local config supports explicit chart source overrides via:
  - `chart_source_overrides`
- Logs now show chart-source candidate diagnostics and whether the final chart source came from:
  - override
  - cached discovery candidates
  - targeted market search
  - fallback to the selected product EPIC

## Historical Candle Foundation

- Historical candles are now treated as a separate market-data foundation from the tradable
  barrier/option product.
- The app distinguishes between:
  - `selected_product_epic`
  - `chart_source_epic`
  - cached/REST historical candles
  - live streaming candles merged into the same series
- For barrier/option products, historical REST on the product EPIC may fail even with very small
  requests such as `120` points.
- The chart therefore prefers an underlying cash/DFB EPIC when one can be resolved.
- Config now supports default and user-editable chart-source overrides, including:
  - `US Tech 100 -> IX.D.NASDAQ.IFD.IP`
- When a chart-source override is used, logs explicitly report:
  - `Chart source resolved via override`
- Successful history loads are cached by:
  - environment
  - account marker
  - `chart_source_epic`
  - resolution
  - price basis
  - range key
  - max points
- If REST history later fails, cached history remains displayable and the UI reports:
  - `Using cached history; live chart continues.`
- The canonical candle series is now owned outside the chart widget and is intended to be the
  basis for future indicators.
- Live chart fidelity now prefers the direct IG chart scale matching the UI interval:
  - `1MINUTE`
  - `5MINUTE`
  - `15MINUTE`
  - `30MINUTE`
  - `HOUR`
- If the direct scale is rejected, the app falls back to `1MINUTE` stream data and aggregates
  locally into the selected timeframe, without displaying raw 1-minute candles on a 5-minute UI.

## Historical REST unavailable / local streaming cache

- IG historical REST may still return:
  - `error.public-api.exceeded-account-historical-data-allowance`
  even for very small requests on a valid cash/DFB chart EPIC.
- When this happens on a `CASH_OR_DFB` chart source, the GUI stops retrying historical REST for
  that account/session instead of burning the full fallback ladder repeatedly.
- Logs explicitly show:
  - `historical_rest_blocked=true`
  - `reason=historical-data-allowance`
  - failed epic / resolution / points
- Live `CHART` streaming remains usable even when historical REST is unavailable.
- Completed live candles are now stored locally under:
  - `~/.trading_ig_assistant/cache/stream_candles/`
- The local stream-candle cache is keyed by:
  - environment
  - account marker/hash
  - chart source epic
  - interval seconds
  - price basis
- No credentials, CST/XST tokens, API keys, passwords, or raw account IDs are written to this
  cache.
- On product selection/startup, the app now:
  1. resolves `chart_source_epic`
  2. loads cached stream candles first if present
  3. displays cached candles immediately
  4. attempts REST backfill only if historical REST is not paused
  5. starts/continues live streaming
- If REST history succeeds, it is merged with cached/local stream candles without duplicates.
- If REST history fails and no cache exists yet, the UI reports:
  - `No historical cache yet. Live candles will be stored from now on.`
- If REST history is blocked but cache exists, the UI reports:
  - `Using cached history; live chart continues.`
- CLI diagnostics now include:
  - `history-market --account-id ...`
  - `history-smoke`
- Recommended manual smoke test:
  - `trading-ig-assistant history-smoke --environment live --epic IX.D.NASDAQ.IFD.IP`
  - `trading-ig-assistant history-market --environment live --epic IX.D.NASDAQ.IFD.IP --resolution MINUTE_5 --max-points 120 --account-id <masked-account>`
