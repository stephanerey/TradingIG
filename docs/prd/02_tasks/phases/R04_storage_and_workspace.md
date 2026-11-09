# R04 — storage and workspace

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-10-22

**Status:** COMPLETED on 2026-10-22. Verified offline with temporary databases and native Qt tests; no broker execution or automatic runtime database activation.

**Prerequisite:** [R03](R03_accounts_and_risk.md) completed with actual evidence. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Design/test event storage, recorder, P&L aggregation and validated Windows workspace/settings.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

Schema/backup/recovery require review; no destructive migration implied.

## Acceptance criteria

Demonstrate reproducible totals, append-only events, recoverable migration and persisted settings/layouts.

Evidence: `docs/codex/tasks/2026-10-22_r04-storage-workspace/verification.md` records schema/recovery, journal, P&L and workspace checks.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

## Requirement references

- [Source chapter 12](../../30_feature/F012_windows_workspace_and_settings.md)
- [Source chapter 13](../../30_feature/F009_trade_journal_and_analytics.md)
- [Source chapter 17](../../10_architecture/domain_contracts.md)
