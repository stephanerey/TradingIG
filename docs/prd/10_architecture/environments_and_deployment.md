# Environments and Deployment

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

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

## V1.2 scope alignment

ANALYSIS/SUPERVISED/AUTO are modes; PAPER/DEMO/LIVE are execution environments. Safe start is ANALYSIS. Continuous V1 operation keeps the GUI open, without implying a Windows service. No live activation during SR00–R06.

Canonical requirements: [chapter 9](../30_feature/F007_software_pending_orders.md), [chapter 12](../30_feature/F012_windows_workspace_and_settings.md), [chapter 16](security_and_auth.md).
