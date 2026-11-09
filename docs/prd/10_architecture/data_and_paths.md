# Data and Paths

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

## Local data root
Use platform-appropriate application data directory, e.g.:
- Windows: `%APPDATA%/TradingIGAssistant/`
- Linux: `~/.local/share/trading_ig_assistant/`

## Files
| Path | Content | Contains secrets? |
|---|---|---:|
| `config/settings.yaml` | Non-secret app settings, watchlists, risk defaults | No |
| `data/trading_ig_assistant.sqlite` | Journal, candles cache, product cache, events | No secrets |
| `logs/app.log` | Redacted application logs | No secrets |
| `exports/` | User exports | No secrets by default |
| OS keyring | IG username/password/API key/token if retained | Yes |

## Data retention
- Journals should be kept indefinitely unless user deletes them.
- Candle cache may be pruned or rebuilt.
- API tokens should be ephemeral or stored only if required and safe.

## Acceptance criteria
- Deleting local data does not delete OS keyring secrets unless user asks.
- Logs and exports pass redaction checks.

## Testing notes
- Unit tests use temp directories.

## V1.2 scope alignment

Preserve existing cache/configuration locations until reviewed migration. Require idempotence, atomic persistence, UTC storage, provenance, pseudonymized exports and documented recovery.

Canonical requirements: [chapter 6](../30_feature/F003_realtime_market_data_and_charts.md), [chapter 13](../30_feature/F009_trade_journal_and_analytics.md), [chapter 16](security_and_auth.md).
