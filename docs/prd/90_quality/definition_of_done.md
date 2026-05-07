# Definition of Done

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

A change is done only when:
- relevant PRD files are referenced in the PR/commit notes;
- code is typed and structured according to package boundaries;
- unit tests pass;
- external API calls are behind adapters and can be mocked;
- no credentials, tokens, account IDs, or raw auth headers are logged;
- user-facing errors are clear and actionable;
- risk-affecting logic has tests;
- journal/event logging is updated when behavior affects trades;
- demo/dry-run behavior is verified before live-capable code is enabled;
- documentation is updated for new settings or workflows.

## Trading-specific gates
- New order or stop-update paths MUST have a dry-run mode.
- Live execution MUST be disabled by default.
- Risk engine MUST be called before any order placement/update action.
- Stale market data MUST block triggers and execution.
- User overrides MUST be logged.
