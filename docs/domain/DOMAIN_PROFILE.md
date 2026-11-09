# TradingIG domain profile

TradingIG is a Windows desktop assistant for market analysis and progressively supervised trading workflows. The current runtime is analysis/read-only: broker connectivity and market data are available, but broker order creation, modification and closing remain disabled.

## R03 boundary

- Accounts are identified by broker, environment and account ID.
- Risk decisions are deterministic and independent from technical or AI scores.
- Portfolio limits span active accounts and canonical economic underlyings.
- Unknown critical account, FX or exposure state vetoes a new opening.
- R03 may assess and reserve risk; it cannot execute an order.

Sources: `docs/prd/30_feature/F001_ig_connection_and_settings.md`, `F006_ticket_builder_and_risk_engine.md`, `F007_software_pending_orders.md` and `docs/prd/02_tasks/phases/R03_accounts_and_risk.md`.
