# Main Flows

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Flow 1 — Configure and connect to IG
1. User opens Settings.
2. User enters IG username, password, API key, environment DEMO/LIVE, optional account ID.
3. App stores secrets via `CredentialProvider`; non-secrets go to config file.
4. `IGRestAdapter` authenticates and retrieves session/account metadata.
5. UI displays connection status and selected account.
6. `IGStreamingAdapter` starts only after REST session succeeds.

## Flow 2 — Select product and view chart
1. User selects a market from watchlist or search.
2. `ProductDiscoveryService` lists available Barrier/Option contracts where API support allows it.
3. User selects product/contract/knock-out/expiry.
4. `MarketDataService` loads historical candles via REST.
5. Streaming quotes update live chart and current bid/ask.
6. Chart overlays show current price, KO, stop, limit, entry, R/R labels.


## Flow 2b — Global market context ribbon
1. After IG connection and provider initialization, `MacroContextService` retrieves configured macro/calendar/news/market-proxy data.
2. Service normalizes signals into `MacroRibbonState` with red/yellow/green/gray indicators.
3. UI displays the ribbon below the menu bar and keeps it visible while the user changes instruments or charts.
4. Clicking a ribbon tile opens details: source, timestamp, confidence, freshness and explanation.
5. Scanner, ticket builder, pending-order engine and journal consume the same snapshot.
6. If a critical provider becomes stale, the ribbon updates state and trading flows receive warnings.

## Flow 3 — Pre-trade analysis and ticket generation
1. Scanner computes trend/structure/relative-strength score.
2. Macro/news engine adds context flags and the current Global Market Context Ribbon snapshot.
3. User requests a ticket or accepts a recommended setup.
4. `TicketBuilder` proposes direction, KO, quantity, stop, limit.
5. `RiskEngine` validates risk, max exposure, R/R, KO distance, account capital.
6. UI displays ticket and warnings.
7. User manually places or confirms the ticket depending on enabled execution mode.

## Flow 4 — Software pending order
1. User defines trigger type: breakout, pullback, price level, candle close, hold time.
2. Pending order enters `ARMED` state.
3. Streaming data updates condition evaluator.
4. If trigger is met, app revalidates spread, staleness, risk, market status, and entry tolerance.
5. App enters `TRIGGERED` state and alerts user with the prepared ticket.
6. User confirms or cancels.
7. Executed or manually placed trades are linked to journal and trade manager.

## Flow 5 — Trade monitoring and dynamic stop management
1. Open position is detected via API or manually linked.
2. Trade manager records entry, initial stop, limit, initial R.
3. State starts as `OPEN`.
4. At configured threshold, stop moves to break-even or better: `PROTECTED`.
5. At later threshold, trailing rules activate: `TRAILING`.
6. Stop updates are either recommended to user or sent via API if enabled/supported.
7. At close, final result is recorded: `CLOSED`.

## Flow 6 — Post-trade analytics
1. Journal stores all events.
2. Analytics computes PnL, R multiple, win/loss, expectancy, max drawdown.
3. User reviews whether rules helped or hurt performance.

## Acceptance criteria
- Each flow can be run in dry-run/demo mode.
- Every state transition creates a journal event.
- Trading actions are blocked if connection/data/account status is invalid.

## Testing notes
- Use replay data to test flows 3–5 without market connectivity.
