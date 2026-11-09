# Testing Strategy

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

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

## V1.2 scope alignment

For this documentary delivery, check links/anchors, coverage, preserved files and Git scope. Installation commands above are not part of consolidation. Future application checks remain pytest -q, ruff check src tests and native Windows Qt smoke as relevant. Network/credential integration is opt-in; critical regression coverage remains required.

Canonical requirements: [chapter 18](../05_coding_agent/sr41_development_workflow.md), [chapter 19](acceptance_matrix.md), [chapter 22](definition_of_done.md).
