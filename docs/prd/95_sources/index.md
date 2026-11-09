# Sources Index (Annotated)

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) apply; original project text is retained and explicit scope changes are recorded in [decisions](../01_product/decisions.md).


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

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

## V1.2 reconstruction source set — 2026-10-22

Source archive: TradingIG_PRD_V1.1_SR4.1_Pack_Codex.zip from the user's local Downloads. SHA-256: E5D724BE71398269AA92E0FE48857758D03868786A25EF6CD40E1339D3E00F6B. All 41 matching downloads were identical. Five Markdown inputs are archived below; the corresponding PDF is not duplicated because its Markdown counterpart is retained.

The original conversation V1.2 could not be recovered. The user authorized reconstruction from V1.1. Archived prompts/audits remain historical source material, not executable task instructions or a competing normative PRD. Claims about published SR versions and API capabilities require future verification.

- S-004: [PROMPT_CODEX_TradingIG_Reprise_R00_R01_SR4.1.md](md/PROMPT_CODEX_TradingIG_Reprise_R00_R01_SR4.1.md).
- S-005: [TradingIG_Addendum_SR_Method_4.1.md](md/TradingIG_Addendum_SR_Method_4.1.md).
- S-006: [PRD_TradingIG_V1.1_SR4.1_2026-10-20.md](md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md).
- S-007: [TradingIG_Audit_Reprise_2026-10-20.md](md/TradingIG_Audit_Reprise_2026-10-20.md).
- S-008: [PROMPT_CODEX_TradingIG_SR00_Upgrade_SR4.1.md](md/PROMPT_CODEX_TradingIG_SR00_Upgrade_SR4.1.md).

[Chapter coverage](../00_conventions/v1_2_source_coverage.md) records the canonical location of each imported chapter.

Source transcription note: Markdown hard breaks written as trailing double spaces are normalized to backslash hard breaks; final newlines are normalized. Requirement wording and identifiers are unchanged. The ZIP hash identifies the byte-original source, not these normalized Markdown transcriptions.
