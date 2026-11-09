# Decisions

## Confirmed

- Settings precedence is `global -> account -> strategy -> market`; later levels override earlier levels.
- R03 remains analysis-only and cannot add a broker execution path.

- Create local skill `codex-tradingig-accounts-risk` from the reconstructed V1.2 PRD and existing code/tests; validated by the user on 2026-10-22.
- Keep reservations in memory for R03; persistence and recovery semantics belong to R04 and later execution coordination.
- Risk-reducing actions remain assessable after the daily opening limit, while broker order methods remain disabled.
