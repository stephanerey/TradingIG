# Tasks Now

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Board
| ID | Title | Status | Owner | Depends | PRD ref | Notes |
|---|---|---|---|---|---|---|
| T-0001 | Create Python project skeleton | TODO | Codex |  | `10_architecture/package_layout.md` | Use src layout and test scaffold |
| T-0002 | Implement settings + credential storage abstraction | TODO | Codex | T-0001 | `30_feature/F001_ig_connection_and_settings.md`, `10_architecture/security_and_auth.md` | No plaintext secrets |
| T-0003 | Implement IG REST demo login spike | TODO | Codex | T-0002 | `30_feature/API001_ig_rest_adapter.md` | Read-only first |
| T-0004 | Fetch account list and configured market snapshots | TODO | Codex | T-0003 | `30_feature/API001_ig_rest_adapter.md` | US Tech, France 40, Germany 40, Spot Gold |
| T-0005 | Research Barrier/Option product discovery and API trading support | TODO | Codex | T-0003 | `30_feature/F002_product_discovery_and_selection.md` | Produce findings in `20_refactor/codebase_findings.md` or a new spike note |
| T-0006 | Implement candle data model and local SQLite schema | TODO | Codex | T-0001 | `10_architecture/data_schema.md` | No UI yet |
| T-0007 | Implement risk engine unit tests | TODO | Codex | T-0001 | `30_feature/F006_ticket_builder_and_risk_engine.md` | Long/short, R/R, max risk |
| T-0008 | Implement trade-manager state-machine unit tests | TODO | Codex | T-0001 | `30_feature/F008_trade_monitor_and_dynamic_stop_manager.md` | OPEN/PROTECTED/TRAILING/CLOSED |
| T-0009 | Add MacroRibbonState model and ribbon UI skeleton | TODO | Codex | T-0001, T-0006 | `30_feature/F011_global_market_context_ribbon.md` | Static/mock data first; no provider dependency in UI |
| T-0010 | Add mocked macro/news provider and aggregate status tests | TODO | Codex | T-0009 | `30_feature/F005_macro_news_context_engine.md`, `30_feature/F011_global_market_context_ribbon.md` | Deterministic red/yellow/green/gray states |

## Done (recent)
| ID | Title | Date | Notes |
|---|---|---|---|
|  |  |  |  |
