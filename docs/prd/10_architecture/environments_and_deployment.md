# Environments and Deployment

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Environments
| Environment | Purpose | Trading allowed | Notes |
|---|---|---:|---|
| `test` | Unit tests with mock adapters | No | No credentials |
| `dry_run` | Real/replay data, no broker execution | No | Default for rule development |
| `demo` | IG demo account integration | Demo only | Required before live |
| `live_manual` | Live account data and manual confirmation | Manual only | MVP maximum live mode |
| `live_auto` | Future explicit automation | Optional future | Out of MVP |

## Deployment
- Local desktop application.
- No cloud backend required in MVP.
- User data stored locally.
- Secrets stored in OS keyring.

## Live-mode gate
Live mode MUST require:
- explicit user toggle;
- visible account type indicator;
- confirmed max-risk settings;
- kill switch;
- successful demo test before activation.

## Acceptance criteria
- App clearly displays current environment.
- Live mode cannot be enabled accidentally.
- Dry-run is the default for development.

## Testing notes
- Unit tests verify that execution calls are blocked outside allowed modes.
