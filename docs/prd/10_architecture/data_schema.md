# Data Schema

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-23

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

## V1.2 scope alignment

The existing table sketches are incomplete target designs. Add account/broker/environment identity, FX/source provenance, candle basis/revision/quality, immutable intents and confirmations, snapshots, rejected signals and configuration/context/model versions. Precision and migrations must preserve financial calculations and append-only audit. Only the deployed subsets recorded below are implemented.

Canonical requirements: [chapter 5](../30_feature/F001_ig_connection_and_settings.md), [chapter 6](../30_feature/F003_realtime_market_data_and_charts.md), [chapter 13](../30_feature/F009_trade_journal_and_analytics.md), [chapter 17](domain_contracts.md).

## R04 implemented subset — 2026-10-22

Schema v1 implements `schema_migrations` and append-only `journal_events` with unique IDs, UTC timestamps, sanitized JSON payloads, Decimal-as-text P&L and explicit P&L status/currency. Update/delete triggers enforce immutability. Initialization is explicit, refuses unknown schemas, backs up existing version changes, restores on failure and validates schema/integrity before WAL use. Broader ticket/position/candle tables remain future work and are not inferred as deployed.

## Paper checkpoint subset — schema v2 — 2026-10-23

After explicit human authorization, schema v2 adds `paper_session_snapshots`. Each row is an
append-only, versioned full checkpoint identified by `snapshot_id`, `session_id` and UTC save time;
the canonical JSON payload stores Decimal values as text and is protected by SHA-256. Update/delete
triggers reject mutation. Migration from v1 creates a recoverable backup first and restores it on
failure. The application performs no database I/O at import or startup: save and restore require
visible user actions. Payload validation rejects credential-like keys and stores no IG account
identity. This is local Paper recovery, not broker reconciliation or proof of IG execution.
