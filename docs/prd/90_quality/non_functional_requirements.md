# Non-functional Requirements

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

## Performance
- UI should remain responsive during streaming updates.
- Quote-to-chart latency target: < 500 ms inside the app after adapter event is received.
- Pending-order evaluation target: < 1 s after receiving relevant quote/candle event.

## Reliability
- REST calls must have timeouts and retry policy where safe.
- Streaming disconnects must be detected and surfaced.
- Order state unknown = automation frozen until user review.

## Security & privacy
- No plaintext secrets in repository, config, logs, exports, or tracebacks.
- OS keyring or equivalent secure storage required for persistent credentials.
- Redaction tests required.

## Observability
- Structured event log for trade lifecycle.
- User-visible connection/account/stream status.
- Debug logs with redacted external API status.

## Compatibility
- Python 3.12+.
- Windows primary desktop target.
- Headless core tests on Linux/WSL.

## Safety
- Demo/dry-run first.
- Live execution explicit and visible.
- Max risk and max exposure hard gates.

## V1.2 scope alignment

Chapter 15.3 targets are measurements, not guaranteed broker latency. Preserve Qt responsiveness, coalesced updates, safe degradation, recoverable caches/audit and explicit unknown data. Network/AI failure must not block local state management.

Canonical requirements: [chapter 6](../30_feature/F003_realtime_market_data_and_charts.md), [chapter 15](../30_feature/F013_alerts_diagnostics_and_resilience.md), [chapter 16](../10_architecture/security_and_auth.md).
