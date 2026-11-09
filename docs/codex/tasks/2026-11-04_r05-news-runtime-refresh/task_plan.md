# Task plan — R05 official news runtime refresh

## Objective

Connect the bounded Fed/ECB collectors to the desktop runtime without blocking the Qt event loop,
while displaying source health only and preserving unknown market direction.

## Smallest sufficient approach

1. Convert collection snapshots into one non-directional source-health signal.
2. Run collection in a `QObject` worker moved to a `QThread`.
3. Refresh once at startup and every 15 minutes, with an explicit manual action.
4. Keep tests offline through injected providers; production supplies the official factories.
5. Verify source-health degradation, Qt responsiveness and protected execution boundaries.

## Scope

Allowed: existing public read-only Fed/ECB providers, Qt orchestration, source-health ribbon state,
offline synthetic tests and focused documentation.

Forbidden: headline interpretation, directional score, AI call, persistence, credential use, IG
mutation, Paper fill, DEMO/LIVE/AUTO order, dependency or GUI redesign.

## Skill

- `codex-tradingig-analysis-scanner`
