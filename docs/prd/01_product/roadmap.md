# Roadmap

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Phases overview
- **P00 Bootstrap:** repo skeleton, secure settings, IG demo login, API capability spike, read-only market snapshot.
- **P20 Architecture:** domain model, adapters, event bus, persistence, chart data model, risk engine boundaries.
- **P30 Features (MVP):** product selector, IG-like charts, scanner, ticket builder, software pending orders, trade monitor, journal.
- **P90 Hardening/Quality:** demo soak tests, replay tests, credential audit, error handling, documentation, live-mode gate.

## Milestones
| Milestone | Date (target) | Definition | Notes |
|---|---|---|---|
| M1 | TBD | IG demo login + market snapshot works | No trading actions |
| M2 | TBD | Streaming prices rendered on chart | Stale-feed detection included |
| M3 | TBD | Ticket builder + risk engine unit-tested | Manual ticket workflow |
| M4 | TBD | Software pending-order monitor works in dry-run | Manual assisted trigger |
| M5 | TBD | Trade monitor + journal replayable | Dynamic stop logic tested |
| M6 | TBD | MVP demo trading session validated | Before any live mode |
