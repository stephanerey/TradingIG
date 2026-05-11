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
