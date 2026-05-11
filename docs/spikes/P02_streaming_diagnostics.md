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
