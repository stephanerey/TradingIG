# R03 rule reference

Authoritative sources:

- `docs/prd/30_feature/F001_ig_connection_and_settings.md` — REQ-ACC-001–007.
- `docs/prd/30_feature/F006_ticket_builder_and_risk_engine.md` — REQ-RISK-001–011 and AC-RISK-001–005.
- `docs/prd/30_feature/F007_software_pending_orders.md` — analysis-only and coordinator boundaries.
- `docs/prd/90_quality/acceptance_matrix.md` — AC-005–008, AC-014 and AC-019.
- `docs/prd/01_product/decisions.md` — deterministic non-overridable vetoes.
- `docs/domain/BUSINESS_RULES.md` and `RISK_REGISTER.md` — compact maintained domain view.

Human decision on 2026-10-22: settings precedence is `global -> account -> strategy -> market`.

R03 implements risk assessment and local reservations only. It does not submit, update or close broker orders and must preserve `LiveTradingDisabledError`.
