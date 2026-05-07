# Handoff — IG Trading Assistant

**Last updated:** 2026-05-07

## Context
Build a Python desktop assistant for IG trading workflows. The user wants strong engineering structure, testable core logic, and safe demo-first integration.

## Read first
- `PRD.md`
- `01_product/product_brief.md`
- `10_architecture/overview.md`
- `10_architecture/security_and_auth.md`
- `30_feature/feature_index.md`
- `02_tasks/tasks_now.md`

## Initial implementation order
1. Create package skeleton.
2. Implement settings and credential provider with mock + keyring backend.
3. Implement IG REST adapter demo login and read-only calls.
4. Implement domain models and SQLite schema.
5. Implement risk engine and trade manager with tests.
6. Implement UI only after core models are stable.

## Hard rules
- No live execution in first implementation pass.
- No secrets in code/config/logs/tests.
- Every broker call behind adapter.
- Every risk-affecting rule unit-tested.
