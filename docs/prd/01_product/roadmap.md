# Roadmap

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

## Phases overview
- **P00 Bootstrap:** repo skeleton, secure settings, IG demo login, API capability spike, read-only market snapshot.
- **P20 Architecture:** domain model, adapters, event bus, persistence, chart data model, risk engine boundaries.
- **P30 Features (MVP):** product selector, IG-like charts, scanner, ticket builder, software pending orders, trade monitor, journal.
- **P90 Hardening/Quality:** demo soak tests, replay tests, credential audit, error handling, documentation, live-mode gate.

## Milestones
| Milestone | Date (target) | Definition | Notes |
|---|---|---|---|
| M1 | TBD | IG demo login + market snapshot works | No trading actions |
| M2 | TBD | Streaming prices rendered on chart | Stale-feed detection included |
| M3 | TBD | Ticket builder + risk engine unit-tested | Manual ticket workflow |
| M4 | TBD | Software pending-order monitor works in dry-run | Manual assisted trigger |
| M5 | TBD | Trade monitor + journal replayable | Dynamic stop logic tested |
| M6 | TBD | MVP demo trading session validated | Before any live mode |

## V1.2 scope alignment

Preserve Pxx history without resetting or marking milestones complete. Chapter 18 gives the canonical restart plan. Current work is documentation only; next eligible action is SR00 preview, not installation or R00.

Canonical requirements: [chapter 18](../05_coding_agent/sr41_development_workflow.md), [chapter 19](../90_quality/acceptance_matrix.md).

## Current restart sequence

| Phase | Canonical scope | Prerequisite | Status |
|---|---|---|---|
| [SR00](../02_tasks/phases/SR00_method_upgrade.md) | Read-only inspection and official SR 4.1 migration preview. Upgrade only after approval of its exact file list. | Separate preview task | NOT_STARTED |
| [R00](../02_tasks/phases/R00_baseline.md) | Reassess the existing application, branch, environment, dependencies and baseline checks. | SR00 | NOT_STARTED |
| [R01](../02_tasks/phases/R01_ohlc_reliability.md) | Address source-reported quota/cache, M1 aggregation and blocking GUI I/O defects only after reproduction. | R00 | NOT_STARTED |
| [R02](../02_tasks/phases/R02_adapter_contracts.md) | Define broker/data contracts, capabilities and instrument mappings incrementally. | R01 | NOT_STARTED |
| [R03](../02_tasks/phases/R03_accounts_and_risk.md) | Implement explicit account state and conservative portfolio risk checks. | R02 | NOT_STARTED |
| [R04](../02_tasks/phases/R04_storage_and_workspace.md) | Design/test event storage, recorder, P&L aggregation and validated Windows workspace/settings. | R03 | NOT_STARTED |
| [R05](../02_tasks/phases/R05_analysis_and_scanner.md) | Implement reproducible indicators, strategies, context and explainable scanner. | R04 | NOT_STARTED |
| [R06](../02_tasks/phases/R06_paper_and_trade_manager.md) | Validate ticket, pending, protection/trailing and alerts using PaperBroker. | R05 | NOT_STARTED |
| [R07](../02_tasks/phases/R07_ig_demo_and_supervised_gate.md) | Collect IG CFD/Barriers/Options capability evidence and validate demo/supervised execution gates. | R06 | NOT_STARTED |
| [R08](../02_tasks/phases/R08_optional_automation.md) | Consider optional automation only after quantitative and safety validation. | R07 | NOT_STARTED |
