# Data Schema

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Goal
Define persistent data needed for journaling, replay, analytics, and cache.

## Initial SQLite tables
### `instruments`
| Field | Type | Notes |
|---|---|---|
| `id` | TEXT PK | Internal ID |
| `epic` | TEXT | IG EPIC when available |
| `name` | TEXT | Display name |
| `market_type` | TEXT | index, commodity, option, barrier, etc. |
| `currency` | TEXT | EUR, USD, etc. |
| `metadata_json` | TEXT | Raw sanitized metadata |

### `product_contracts`
| Field | Type | Notes |
|---|---|---|
| `id` | TEXT PK | Internal product ID |
| `underlying_instrument_id` | TEXT | FK-ish reference |
| `product_type` | TEXT | barrier, option, cfd, etc. |
| `epic` | TEXT | Product EPIC if distinct |
| `direction` | TEXT | BUY/SELL capable or call/put depending product |
| `expiry` | TEXT | As exposed by IG |
| `knockout_level` | REAL | Barrier/KO if applicable |
| `min_size` | REAL | Product constraint |
| `currency` | TEXT | Pricing currency |
| `last_snapshot_json` | TEXT | Sanitized product data |

### `candles`
| Field | Type | Notes |
|---|---|---|
| `instrument_id` | TEXT | |
| `timeframe` | TEXT | 1m, 5m, 1h |
| `ts` | TEXT | UTC ISO timestamp |
| `open` | REAL | |
| `high` | REAL | |
| `low` | REAL | |
| `close` | REAL | |
| `volume` | REAL NULL | If available |

### `tickets`
Stores generated ticket proposals and accepted tickets.

### `positions`
Stores linked/open/closed positions.

### `pending_orders`
Stores software pending orders and their states.

### `journal_events`
Append-only event log: recommendation, ticket built, pending trigger, user confirm/cancel, order update, stop move, exit, error.


### `macro_context_snapshots`
Stores compact snapshots of the Global Market Context Ribbon for replay and audit.

| Field | Type | Notes |
|---|---|---|
| `id` | TEXT PK | Snapshot ID |
| `ts` | TEXT | UTC ISO timestamp |
| `regime` | TEXT | risk_on, neutral, risk_off, unknown |
| `index_bias` | TEXT | bullish, neutral, bearish, unknown |
| `gold_bias` | TEXT | bullish, neutral, bearish, unknown |
| `event_risk` | TEXT | low, medium, high, unknown |
| `signals_json` | TEXT | Sanitized array of ContextSignal objects |
| `provider_health_json` | TEXT | Provider freshness/error summary |

### `ticket_context_links`
Links generated tickets/trades to the macro ribbon state visible at decision time.

| Field | Type | Notes |
|---|---|---|
| `ticket_id` | TEXT | Ticket/recommendation ID |
| `macro_context_snapshot_id` | TEXT | Snapshot ID |


## Constraints
- Raw broker responses may be stored only after secret/token redaction.
- Journal events should be append-only.
- Timestamps MUST be UTC internally.

## Acceptance criteria
- Schema supports replay of a complete trade lifecycle.
- Every order/stop update can be traced to a rule or user override.

## Testing notes
- Migration tests create a fresh database and verify schema.
