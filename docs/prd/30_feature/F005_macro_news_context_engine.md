# F005 — Macro / News Context Engine

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Provide a market-context panel that summarizes macroeconomic and geopolitical drivers likely to affect index and gold trades.

## Non-goals
- The module must not automatically trade based only on news.
- The module must not scrape restricted/paywalled sources without permission.

## Requirements
- Track scheduled macro events: Fed/FOMC, ECB where relevant, CPI, jobs reports, GDP, PMI, central-bank speeches.
- Track broad risk context: geopolitical tension, Middle East headlines, oil shocks, dollar index, US yields, VIX/risk sentiment where providers are available.
- Display upcoming high-impact events and time-to-event.
- Display current context summary: risk-on, risk-off, gold-supportive, dollar/yield pressure, event-risk warning.
- Attach source, timestamp, and confidence/status to each context item.
- Produce risk flags used by scanner/ticket builder, e.g. `HIGH_EVENT_RISK`, `GAP_RISK`, `NEWS_DRIVEN_MARKET`.
- Produce a normalized `MacroRibbonState` consumed by the Global Market Context Ribbon.
- For each context item, output: severity (`GREEN`/`YELLOW`/`RED`/`GRAY`), short label, summary, source, timestamp, confidence, and freshness.
- Compute aggregate status: global regime, index bias, gold bias, and event risk.

## Constraints
- Provider selection is configurable.
- Do not store copyrighted full articles; store metadata, summary, URL, timestamp, and tags.
- Context must be clearly separated from trade recommendation.

## Acceptance criteria
- User can see upcoming high-impact macro events.
- Scanner can display macro flags next to technical score.
- News provider failures degrade gracefully.

## Testing notes
- Mock calendar/news providers.
- Unit-test context classification from structured events.

## Related UI
See `F011_global_market_context_ribbon.md` for the persistent red/yellow/green status band shown below the menu bar.
