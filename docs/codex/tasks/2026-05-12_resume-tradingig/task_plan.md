# Resume TradingIG Task Plan

Date: 2026-05-12

## Goal

Rebuild a clean task memory after recovery context import, without modifying application code.

## Plan

1. Verify workspace and git history.
2. Read available local instructions and project state files.
3. Read recovery context as historical context only.
4. Inspect project metadata and README.
5. Inspect recent commits.
6. Map files for historical candles, streaming candles, caches, IG REST, Lightstreamer, and chart UI.
7. Compare recovery-context claims with code and git evidence.
8. Write structured resume docs under `docs/`.
9. Report remaining problem, candidate files, proposed minimal patch, verification commands, and risks.

## Status

- Workspace verification: done.
- Required file read pass: done.
- Code mapping: done.
- Recovery context comparison: done.
- Documentation update: done in this task directory and `docs/CURRENT_STATE.md`.
- Application code changes: intentionally not done.

## Out Of Scope

- Refactor.
- Bug fix implementation.
- Credential changes.
- Live IG calls with credentials.
- Git staging, commit, or push.
