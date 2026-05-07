# KPIs

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## KPI list
| KPI | Definition | How measured | Target | Notes |
|---|---|---|---|---|
| KPI-01 | IG demo connection reliability | Successful login + account/market fetch attempts / total attempts | > 95% during MVP testing | Exclude IG outages |
| KPI-02 | Streaming freshness | Time since last quote update for subscribed instruments | < 2 s typical during open markets | Alert when stale |
| KPI-03 | Ticket calculation correctness | Unit tests comparing expected risk/PnL/ratio with engine output | 100% pass | Must include long and short cases |
| KPI-04 | Risk-rule enforcement | Oversized or invalid tickets rejected by risk engine | 100% in tests | Includes max risk, max exposure, KO distance |
| KPI-05 | Stop-management consistency | State transitions match deterministic rules in replay tests | 100% pass | OPEN/PROTECTED/TRAILING/CLOSED |
| KPI-06 | Journal completeness | Trades with full event trail | 100% | Entry, updates, exit, reason, PnL |
| KPI-07 | Manual pending-order latency | Time from trigger to user notification | < 1 s after condition evaluation | MVP manual assisted mode |
| KPI-08 | User override traceability | All overrides logged with reason | 100% | Prevent hidden manual drift |

## Measurement plan
- Data source(s): local event log, SQLite database, unit/integration test reports, IG demo session logs.
- Frequency: per development milestone and after every significant trading session.
- Owner: project owner / coding agent during implementation.
