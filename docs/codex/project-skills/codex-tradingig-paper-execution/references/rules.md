# R06 rule reference

Authoritative sources:

- `docs/prd/02_tasks/phases/R06_paper_and_trade_manager.md`.
- `docs/prd/30_feature/F007_software_pending_orders.md` — execution separation, intent lifecycle, trigger revalidation and idempotence.
- `docs/prd/30_feature/F008_trade_monitor_and_dynamic_stop_manager.md` — monotone trade state and non-widening stop rules.
- `docs/prd/30_feature/F010_backtesting_and_replay.md` — deterministic PaperBroker, explicit fill assumptions and no look-ahead.
- `docs/prd/30_feature/F013_alerts_diagnostics_and_resilience.md` — safe degradation and local visibility.
- `docs/domain/BUSINESS_RULES.md`, `RISK_REGISTER.md` and `HUMAN_VALIDATION_RULES.md`.

Human validation on 2026-10-22 covers only deterministic, offline paper behavior. It does not authorize an IG order call, DEMO/LIVE capability activation, AUTO mode, external notification, new dependency or R07 behavior.
