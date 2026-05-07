# Product Brief — IG Trading Assistant

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Problem statement
The user trades IG Barriers/Options manually on instruments such as US Tech 100, France 40, Germany 40, and Spot Gold. The current workflow relies on reading the IG web platform, manually estimating the best trade, selecting a barrier/option, entering quantity/stop/limit, and then manually adjusting the stop after the trade starts moving.

This creates recurring issues:
- entry decisions can be emotional after a winning or losing trade;
- position size can become too aggressive;
- follow-up trades may be opened without checking total exposure;
- stop management is manual and can be late or inconsistent;
- barriers/options do not always expose a convenient delayed-order workflow in the web UI;
- market context from macro/geopolitical news is separate from the technical chart view and is not visible as a compact control/status band during trade preparation.

The product solves this by building a disciplined assistant connected to IG APIs that provides market data, charting, product selection, risk-controlled ticket generation, software pending-order monitoring, dynamic stop management, and journaling.

## Target users / personas
- **Primary user:** Stéphane, technically advanced retail trader, comfortable with Python/PyQt, wants precise control and transparent logic rather than a black-box robot.
- **Secondary future user:** technically literate trader who wants a local desktop trading assistant for IG products with strict risk management and manual confirmation.

## Goals
- **G1:** Connect reliably to IG demo/live environments via REST and Streaming APIs.
- **G2:** Allow the user to choose from available IG Barrier/Option contracts and inspect their constraints before building a ticket.
- **G3:** Display IG-like candlestick charts with trade overlays and real-time updates.
- **G4:** Analyze a small watchlist and rank trade opportunities by technical setup quality and market context.
- **G4b:** Display a persistent Global Market Context Ribbon below the main menu, using red/yellow/green/gray indicators for macro, geopolitical, rate, dollar, oil, volatility and data-health signals.
- **G5:** Generate a complete ticket: instrument/product, direction, quantity, knock-out/barrier, stop, limit, expected loss, target gain, R/R ratio, fees/prime where available.
- **G6:** Provide software pending-order logic for manual assisted entry when native delayed orders are not available or not suitable for the selected product.
- **G7:** Monitor open trades and manage stop updates through deterministic state-machine rules.
- **G8:** Journal every trade, action, recommendation, decision, and outcome for later analysis and backtesting.

## Non-goals
- **NG1:** The MVP is not a fully autonomous live trading robot.
- **NG2:** The app does not guarantee profitable trades and MUST NOT label any trade as risk-free.
- **NG3:** The app does not replace the IG platform; it assists, validates, and optionally invokes supported API actions.
- **NG4:** The MVP does not implement complex machine learning or opaque AI-based execution.
- **NG5:** The macro/news module does not provide legally regulated investment advice; it provides context and risk flags.

## Scope by phase
### P00 Bootstrap
- Create Python project skeleton.
- Implement settings model and secure credential storage abstraction.
- Validate IG demo authentication.
- Retrieve account metadata and market snapshots.
- Record a technical spike about Barriers/Options API support and limitations.

### P20 Architecture
- Implement REST/Streaming boundaries.
- Implement domain models: Instrument, ProductContract, Candle, Quote, Ticket, Position, PendingOrder, TradeState, JournalEvent.
- Implement event bus and persistence layer.

### MVP (P30)
- IG connection configuration screen.
- Product discovery/selection for configured instruments and available Barrier/Option contracts.
- Real-time candle chart with IG-like overlays.
- Watchlist scanner and setup scoring.
- Macro/news context panel and persistent Global Market Context Ribbon.
- Ticket builder and risk validation.
- Software pending-order monitor with manual confirmation.
- Trade monitor with break-even and trailing-stop recommendations or updates where supported.
- Journal and basic analytics.

### V2+
- Optional semi-automated order placement if API support is confirmed and explicitly enabled.
- Advanced chart tools and multi-timeframe analysis.
- ATR/structure-based trailing modes.
- Replay and backtesting of trade-management rules.
- Configurable provider adapters for economic calendar/news.
- Alerting via desktop notification, email, Telegram, or MQTT.

## Constraints
- Python desktop application; PyQt/PySide + pyqtgraph or equivalent charting stack are preferred.
- The user is technically advanced and values modular, testable, object-oriented code.
- IG API coverage for Barriers/Options must be verified early; fall back to manual assisted workflows when an API action is unsupported.
- Demo mode must be supported before live mode.
- API credentials must be configured in the UI but stored securely using OS keyring or equivalent encrypted storage.
- No secrets in repository, logs, journal exports, or screenshots.
- Risk engine must be independent from UI so it can be unit-tested and backtested.

## Success criteria
See `01_product/kpis.md`.
