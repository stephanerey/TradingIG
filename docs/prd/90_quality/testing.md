# Testing Strategy

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Test layers
- Unit tests: risk engine, ticket builder, pending-order state machine, trade manager, candle aggregation, redaction.
- Adapter tests: mocked IG REST/Streaming responses.
- Integration tests: opt-in IG demo connection and read-only data retrieval.
- Replay tests: deterministic market sequences for pending orders and dynamic stops.
- UI smoke tests: settings screen, chart load, ticket display.

## Minimum expectations
- New logic SHOULD have unit tests.
- Risk-affecting logic MUST have unit tests.
- Broker execution paths MUST have dry-run tests before live use.
- Critical flows MUST have integration or replay verification.

## How to run
```bash
pip install -e .[dev]
pytest
ruff check src tests
```

Optional integration tests:
```bash
# Example only. Actual variable names to be defined during implementation.
export TIA_RUN_IG_DEMO_TESTS=1
pytest tests/integration
```

## Test fixtures
- Use fake secrets for redaction tests.
- Use sanitized IG-like JSON fixtures.
- Do not commit real account IDs or tokens.
