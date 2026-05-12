# Decisions

Date: 2026-05-12

## Decisions Made

- Treat `docs/codex/TradingIG_RECOVERY_CONTEXT.md` as historical context only.
- Mark recovery-context-only statements as "a verifier" until confirmed by code or git.
- Do not modify application code in this pass.
- Create a clean task memory under `docs/codex/tasks/2026-05-12_resume-tradingig/`.
- Use `docs/CURRENT_STATE.md` as the current concise project-state entry point.
- Identify price-basis reload behavior as the main code-level candidate for a minimal next patch.

## Decisions Deferred

- Whether to patch price-basis reloading now.
- Whether to update README P02 status to reflect the new candle foundation.
- Whether to add a live credentialed smoke-test checklist or script.
- Whether to split history cache helpers out of `main_window.py`.

## Constraints Preserved

- Read-only trading posture.
- No credential changes.
- No broad refactor.
- No application-code edits.
