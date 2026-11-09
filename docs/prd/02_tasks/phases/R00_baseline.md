# R00 — baseline

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstruction.

**Last updated:** 2026-10-22

**Status:** COMPLETED on 2026-10-22 with project-local environment and offline baseline evidence.

**Prerequisite:** [SR00](SR00_method_upgrade.md) completed with actual evidence. [Canonical source sequence and SR boundaries](../../05_coding_agent/sr41_development_workflow.md).

## Goal

Reassess the existing application, branch, environment, dependencies and baseline checks.

## Non-goals

No task is launched by reading this specification. No automatic branch switch, dependency installation, broker action or deployment.

## Constraints

Do not infer that legacy bootstrap TODOs are unfinished implementation.

## Acceptance criteria

Record pytest, Ruff and native GUI smoke results or concrete limitations; preserve functional code; update factual current state.

## Testing notes

Use phase-appropriate unit/contract/replay or native Windows UI checks from [the acceptance matrix](../../90_quality/acceptance_matrix.md) and [testing strategy](../../90_quality/testing.md). Record actual commands, results and limitations; do not mark acceptance based only on this document.

## Requirement references

- [Source chapter 3](../../20_refactor/codebase_findings.md)
- [Source chapter 18](../../05_coding_agent/sr41_development_workflow.md)
- [Source chapter 19](../../90_quality/acceptance_matrix.md)
