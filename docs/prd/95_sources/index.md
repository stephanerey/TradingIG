# Sources Index (Annotated)

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

## Entries
| ID | Type | Location | Tags | Why it matters | Notes |
|---|---|---|---|---|---|
| S-001 | URL | `links.md` | IG, REST, streaming | Defines official IG API capabilities and constraints used by the app architecture. | REST for snapshots/history/actions; Streaming for real-time prices and updates. |
| S-002 | Conversation | Current ChatGPT project discussion | product, workflow, risk | Captures user workflow: Barriers/Options ticket building, US Tech/France/Germany/Gold watchlist, software pending orders, dynamic stop management. | Source of product requirements. |
| S-003 | Screenshots | Chat conversation attachments | UI, IG platform, chart | Show target visual workflow: IG candlestick charts, ticket panels, stop/limit/KO overlays, positions view. | Not copied into PRD zip unless explicitly requested. |


## Included UI screenshots
Screenshots added to `95_sources/images/` as visual references for the UI specification:

- `ig_workspace_us_tech_trade_candidate.png` — full IG workspace showing the top menu area, instrument tabs, candlestick chart and ticket panel. Use it as reference for placing the Global Market Context Ribbon below the menu/toolbar.
- `ig_us_tech_live_trade_with_positions.png` — chart with active position and horizontal stop/limit/KO overlays.
- `ig_position_stop_adjusted_positive.png` — position panel after stop has been moved above entry.
- `ig_us_tech_barrier_ticket_example.png` — US Tech 100 barrier ticket with KO, quantity, stop, limit, prime and fees.
- `ig_france40_barrier_ticket_example.png` — France 40 barrier ticket example.
- `ig_multi_instrument_daily_context.png` — multi-instrument context view used to compare market setups.
