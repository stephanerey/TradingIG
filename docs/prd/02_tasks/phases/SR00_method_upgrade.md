# SR00 — method upgrade

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-10-22

**Status:** COMPLETED on 2026-10-22 after exact-plan approval; official SR 4.1.0 post-check green.

**Prerequisite:** a separately scoped read-only preview task. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Read-only inspection and official SR 4.1 migration preview. Upgrade only after approval of its exact file list.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

No installer run in this consolidation. A branch name is not evidence that SR is installed.

## Acceptance criteria

Verify official version/release/commit, preserved local customizations, post-install checks and absence of application changes; stop before R00.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

## Requirement references

- [Source chapter 18](../../05_coding_agent/sr41_development_workflow.md)
