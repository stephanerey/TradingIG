# P00 Bootstrap

> **PRD Policy:** **PROJECT (editable)** — Current phase scope.

**Last updated:** 2026-05-07

## Goal
Build the minimal safe foundation: repository skeleton, configuration model, secure credentials, IG demo connection, and first read-only market/account retrieval.

## Non-goals
- No live trading.
- No automatic order execution.
- No complete UI beyond minimal settings/status screen unless trivial.

## Scope
- Python package skeleton with tests.
- Settings model with environment selection: DEMO/LIVE.
- Credential provider abstraction using OS keyring or mock provider for tests.
- IG REST adapter authentication spike.
- Account metadata retrieval.
- Market search/snapshot retrieval for configured instruments.
- API capability note for Barrier/Option products and working orders.

## Acceptance criteria
- Unit tests run locally.
- Demo credentials can be entered without storing secrets in plaintext project files.
- Successful demo login retrieves account metadata.
- Market snapshot retrieval works for at least one configured instrument.
- API errors are logged without leaking secrets.

## Testing notes
- Mock IG HTTP responses for unit tests.
- Use demo environment for integration tests.
- Manual live credentials must not be required in CI.
