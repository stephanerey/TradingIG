# P90 Hardening / Quality

> **PRD Policy:** **PROJECT (editable)** — Hardening phase scope.

**Last updated:** 2026-05-07

## Goal
Make the application safe enough for repeated demo use and, later, controlled live use.

## Non-goals
- No expansion to many markets before core reliability is proven.

## Scope
- Credential redaction audit.
- Error handling and reconnect logic.
- Stale-feed handling.
- Dry-run/live-mode safety gate.
- Replay tests for software pending orders and trade manager.
- Documentation and operator checklist.

## Acceptance criteria
- No known secret leakage path.
- App handles IG disconnect/reconnect without crashing.
- Trading actions are disabled when data is stale or account state is unknown.
- User-visible warnings exist for live mode, over-risk, and override actions.

## Testing notes
- Simulate API failures.
- Simulate streaming disconnects.
- Replay volatile/gap scenarios.
