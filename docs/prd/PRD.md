# PRD — IG Trading Assistant

> **PRD Policy:** **PROJECT (editable)** — Project-specific source of truth for the IG Trading Assistant.

**Status:** Draft ready for P00 bootstrap  
**Owner:** Stéphane  
**Last updated:** 2026-05-07

## Product summary
The IG Trading Assistant is a Python desktop application that connects to the IG REST and Streaming APIs to help a retail trader analyze a short list of IG markets, select an available Barrier or Option contract, build a risk-controlled ticket, monitor the open trade, and manage stops according to deterministic rules.

The application MUST prioritize discipline over activity: it MUST be able to recommend no trade, reject oversized positions, and prevent dangerous workflows such as averaging down, widening stops, or stacking correlated trades without explicit override.

## Scope highlights
- IG account configuration screen: username, password, API key, environment, account selection, token/session status.
- IG REST adapter for authentication, account data, market/product discovery, historical prices, positions, order placement/update/close where supported.
- IG Streaming adapter using Lightstreamer for real-time prices, open positions, account updates, and trade status notifications.
- Product selector for available IG Barriers and Options, including knock-out level, expiry, bid/ask, spread, minimum size, currency, cost/prime, and order constraints.
- IG-like candlestick chart view with overlays for current price, entry, knock-out, stop, limit, risk/reward, PnL, and software pending-order levels.
- Pre-trade market scanner for US Tech 100, France 40, Germany 40, Spot Gold, and other configured instruments.
- News and macro context module covering Fed/FOMC, economic releases, dollar/yields/oil/VIX context, geopolitical risk, and market sentiment, with a red/yellow/green Global Market Context Ribbon directly under the main menu.
- Software pending orders for products where IG does not expose or allow native delayed order workflow in the selected context: monitored by the app, manually confirmed by the user, and never fired blindly in MVP.
- Dynamic trade manager with state machine: OPEN → PROTECTED → TRAILING → CLOSED.
- Risk engine based on capital, max risk, R multiples, product-specific constraints, and total exposure.
- Trade journal, event log, screenshots/notes, and performance analytics.
- Replay/backtest framework to test stop/limit/trailing rules before live automation.

## Mandatory reads for Codex
1. `00_conventions/conventions_and_naming.md`
2. `01_product/product_brief.md`
3. `10_architecture/overview.md`
4. `10_architecture/main_flows.md`
5. `10_architecture/security_and_auth.md`
6. `30_feature/feature_index.md`
7. `90_quality/definition_of_done.md`
8. `02_tasks/tasks_now.md`

## Product documents
- `01_product/product_brief.md`
- `01_product/kpis.md`
- `01_product/risks_and_assumptions.md`
- `01_product/roadmap.md`
- `01_product/decisions.md`
- `01_product/glossary.md`

## Architecture documents
- `10_architecture/overview.md`
- `10_architecture/main_flows.md`
- `10_architecture/runtime_environment.md`
- `10_architecture/environments_and_deployment.md`
- `10_architecture/package_layout.md`
- `10_architecture/module_boundaries.md`
- `10_architecture/data_and_paths.md`
- `10_architecture/data_schema.md`
- `10_architecture/logging_and_errors.md`
- `10_architecture/security_and_auth.md`

## Feature specifications
- `30_feature/F001_ig_connection_and_settings.md`
- `30_feature/F002_product_discovery_and_selection.md`
- `30_feature/F003_realtime_market_data_and_charts.md`
- `30_feature/F004_market_scanner_and_setup_scoring.md`
- `30_feature/F005_macro_news_context_engine.md`
- `30_feature/F006_ticket_builder_and_risk_engine.md`
- `30_feature/F007_software_pending_orders.md`
- `30_feature/F008_trade_monitor_and_dynamic_stop_manager.md`
- `30_feature/F009_trade_journal_and_analytics.md`
- `30_feature/F010_backtesting_and_replay.md`
- `30_feature/F011_global_market_context_ribbon.md`
- `30_feature/API001_ig_rest_adapter.md`
- `30_feature/API002_ig_streaming_adapter.md`
- `30_feature/API003_news_and_macro_adapters.md`

## Current execution phase
Current phase: **P00 Bootstrap**.  
Goal: build a safe skeleton, validate IG API access in demo mode, and implement read-only market data before any live order capability.

## Non-negotiable constraints
- No hardcoded credentials.
- No plaintext password or API key in logs, config files, screenshots, or exceptions.
- Live order execution MUST require explicit user enablement and visible confirmation in MVP.
- The system MUST support demo mode first.
- The app MUST never present any trade as risk-free.
- The app MUST keep an immutable event log for every recommendation, ticket calculation, order change, and stop/limit update.
