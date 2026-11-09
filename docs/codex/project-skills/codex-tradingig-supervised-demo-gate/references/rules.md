# R07 rule reference

Authoritative sources:

- `docs/prd/02_tasks/phases/R07_ig_demo_and_supervised_gate.md`.
- `docs/prd/30_feature/F001_ig_connection_and_settings.md` — credential handling, profile isolation and connection state.
- `docs/prd/30_feature/F006_ticket_builder_and_risk_engine.md` — immutable confirmation, account binding and risk authorization.
- `docs/prd/30_feature/F007_software_pending_orders.md` — trigger revalidation, idempotence and ambiguous execution handling.
- `docs/prd/30_feature/API001_ig_rest_adapter.md` — IG REST boundary and capability evidence.
- `docs/domain/BUSINESS_RULES.md`, `RISK_REGISTER.md` and `HUMAN_VALIDATION_RULES.md`.

Human validation on 2026-10-22 authorizes authenticated IG DEMO calls in read-only mode only. It does not authorize a DEMO order, position or working-order mutation, a LIVE call, relaxation of `LiveTradingDisabledError`, a new dependency or an unredacted evidence capture.
