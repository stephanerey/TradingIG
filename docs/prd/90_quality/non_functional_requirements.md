# Non-functional Requirements

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

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
