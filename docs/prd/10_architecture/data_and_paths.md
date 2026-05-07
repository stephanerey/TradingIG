# Data and Paths

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

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
