# Feature Index

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) apply; original project text is retained and explicit scope changes are recorded in [decisions](../01_product/decisions.md).


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

| ID | Feature | Priority | Phase | Spec |
|---|---|---:|---|---|
| F001 | IG connection and settings | P0 | P00/P30 | `F001_ig_connection_and_settings.md` |
| F002 | Product discovery and Barrier/Option selection | P0 | P00/P30 | `F002_product_discovery_and_selection.md` |
| F003 | Real-time market data and IG-like charts | P0 | P20/P30 | `F003_realtime_market_data_and_charts.md` |
| F004 | Market scanner and setup scoring | P1 | P30 | `F004_market_scanner_and_setup_scoring.md` |
| F005 | Macro/news context engine | P1 | P30 | `F005_macro_news_context_engine.md` |
| F006 | Ticket builder and risk engine | P0 | P20/P30 | `F006_ticket_builder_and_risk_engine.md` |
| F007 | Software pending orders | P0 | P30 | `F007_software_pending_orders.md` |
| F008 | Trade monitor and dynamic stop manager | P0 | P30 | `F008_trade_monitor_and_dynamic_stop_manager.md` |
| F009 | Trade journal and analytics | P1 | P30 | `F009_trade_journal_and_analytics.md` |
| F010 | Backtesting and replay | P2 | V2 | `F010_backtesting_and_replay.md` |
| F011 | Global market context ribbon | P1 | P30 | `F011_global_market_context_ribbon.md` |
| API001 | IG REST adapter | P0 | P00/P20 | `API001_ig_rest_adapter.md` |
| API002 | IG Streaming adapter | P0 | P20/P30 | `API002_ig_streaming_adapter.md` |
| API003 | News and macro adapters | P1 | P30/V2 | `API003_news_and_macro_adapters.md` |

## V1.2 feature and API mapping

The earlier Pxx table is historical; use this mapping for restart dependencies. Phase allocation describes scope, not completion. Original IDs and filenames stay stable.

| ID | Current scope | Restart phases | Spec |
|---|---|---|---|
| API001 | Account-scoped IG REST capability contracts | R02/R03/R07 | [API001](API001_ig_rest_adapter.md) |
| API002 | Lightstreamer data and health contracts | R01/R02/R07 | [API002](API002_ig_streaming_adapter.md) |
| API003 | Licensed news/calendar provider contracts | R05 | [API003](API003_news_and_macro_adapters.md) |
| F001 | Accounts, identity and settings | R03/R04 | [F001](F001_ig_connection_and_settings.md) |
| F002 | Discovery and product capabilities | R02/R07 | [F002](F002_product_discovery_and_selection.md) |
| F003 | OHLC, cache, streaming and quality | R01/R02 | [F003](F003_realtime_market_data_and_charts.md) |
| F004 | Indicators, strategies and explainable scoring | R05 | [F004](F004_market_scanner_and_setup_scoring.md) |
| F005 | Macro, sentiment and AI context | R05/R08 | [F005](F005_macro_news_context_engine.md) |
| F006 | Deterministic risk and ticket sizing | R03/R06 | [F006](F006_ticket_builder_and_risk_engine.md) |
| F007 | Modes, execution and software pending | R06/R07/R08 | [F007](F007_software_pending_orders.md) |
| F008 | Confirmed protection and trade management | R06/R07 | [F008](F008_trade_monitor_and_dynamic_stop_manager.md) |
| F009 | Recorder, rejected signals and analytics | R04 | [F009](F009_trade_journal_and_analytics.md) |
| F010 | Paper validation and quantitative replay | R06 (paper)/R08 (quantitative) | [F010](F010_backtesting_and_replay.md) |
| F011 | Persistent context ribbon | R04/R05 | [F011](F011_global_market_context_ribbon.md) |
| F012 | Windows workspace and validated settings | R04 | [F012](F012_windows_workspace_and_settings.md) |
| F013 | Alerts, diagnostics and resilience | R01/R03/R06 | [F013](F013_alerts_diagnostics_and_resilience.md) |
