# R06 — paper and trade manager

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-10-22

**Status:** COMPLETED locally on 2026-10-22. Evidence: 187 offline tests, targeted Ruff/format checks, complete paper-flow integration and protected IG-order regressions.

**Prerequisite:** [R05](R05_analysis_and_scanner.md) completed with actual evidence. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Validate ticket, pending, protection/trailing and alerts using PaperBroker.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

Broker order methods remain inaccessible to ANALYSIS; no live enabling.

## Acceptance criteria

Complete paper flow, simulated confirmations, state-machine tests and proof of no live calls.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

## Requirement references

- [Source chapter 9](../../30_feature/F007_software_pending_orders.md)
- [Source chapter 10](../../30_feature/F008_trade_monitor_and_dynamic_stop_manager.md)
- [Source chapter 14](../../30_feature/F010_backtesting_and_replay.md)
- [Source chapter 15](../../30_feature/F013_alerts_diagnostics_and_resilience.md)

## Completion evidence and boundary

- Tickets expose entry, spread, fees, slippage, loss/gain, R/R, warnings and an immutable paper intent.
- `PaperBroker` accepts only paper accounts, requires an approved risk decision, is idempotent by intent ID and retains fill/provenance/P&L events.
- Pending orders cover price/zone/hold/candle-close/rebound semantics, expiry, chronological replay, trigger locking and trigger-time freshness, market/product, macro, spread/slippage and risk gates.
- Trade management covers long/short net break-even, fixed-R trailing, cooldown/minimum step, non-widening stops and state changes only after confirmation.
- A deterministic integration scenario runs pending → risk → paper fill → stop confirmation → close → reservation release → journal/alert without an IG adapter.
- This does not validate IG order capabilities, enable DEMO/LIVE execution, claim paper realism or start R07.
- A later analysis-to-Paper boundary can now prepare an immutable ticket draft and its matching
  `RiskRequest` from an exact unexpired `READY` directive. It performs no risk decision,
  reservation, Paper submission or fill; the established R06 gates remain unchanged.
- That proposal may now receive a non-reserving risk review with full decision reasons and setting
  provenance. An approval still grants no broker authorization and opens no position.
- An explicit operator-confirmed boundary can then re-evaluate and reserve risk atomically before
  entering the existing idempotent local Paper coordinator. Changed exposure, rejection or expiry
  blocks the action; no automatic trigger or IG route was added.
