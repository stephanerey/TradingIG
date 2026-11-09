# R03 — accounts and risk

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-10-22

**Status:** COMPLETED on 2026-10-22. Verified offline; no broker execution was added or activated.

**Prerequisite:** [R02](R02_adapter_contracts.md) completed with actual evidence. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Implement explicit account state and conservative portfolio risk checks.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

Resolve settings inheritance before implementing dependent configuration semantics.

## Acceptance criteria

Test FX/unknown exposure, account switch failure, 1%/3% defaults, global/underlying limits, concurrent reservations and vetoes.

Evidence: `docs/codex/tasks/2026-10-22_r03-accounts-risk/verification.md` records targeted and full checks. Settings use the human-approved D-013 precedence.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

## Requirement references

- [Source chapter 5](../../30_feature/F001_ig_connection_and_settings.md)
- [Source chapter 8](../../30_feature/F006_ticket_builder_and_risk_engine.md)
- [Source chapter 9](../../30_feature/F007_software_pending_orders.md)
