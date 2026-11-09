# GUI Paper ticket

## Objective

Replace the P01 ticket placeholder with a compact analysis/Paper proposal view wired to the existing `TicketBuilder` and `RiskEngine`, without creating an execution path.

## Authority and assumptions

- User validated this bounded GUI Paper lot on 2026-10-23.
- R07 is deferred; R08/AUTO, DEMO mutations and LIVE orders remain forbidden.
- The selected product and latest received quote may feed a local preview, but do not prove broker execution capability.
- Unknown/stale quotes, unsupported products and incomplete Barrier KO risk must fail visibly.

## Smallest sufficient approach

1. Implement a scrollable `PaperTicketWidget` in the existing placeholder module.
2. Feed it only the selected `TradableProduct` and received `Quote` from `ProductSelectorWidget`.
3. Build a paper-only `TicketDraft`, evaluate it against a local confirmed Paper account snapshot, and display estimates, warnings and rejection reasons.
4. Expose no submit/execute button, broker adapter or `PaperBroker` fill action.
5. Keep market details and ticket in compact tabs so the 960×600 viewport remains usable.

## Selected skills

- `codex-tradingig-paper-execution` — enforce the paper-only structural boundary.
- `aurora-ui-visual-qa` — native Qt layout and viewport verification.

`python-pyqt-threading` is referenced by legacy `AGENTS.md` but absent from the installed local pack. No worker/thread change is needed in this lot.

## Planned proof

- Widget unit tests for approved preview, risk rejection, stale quote and Barrier KO requirements.
- Integration test proving selection/quote propagation without a broker execution method.
- Targeted Ruff/format, protected IG-order tests, full offline suite and native offscreen Qt screenshot/viewport inspection.

## Quote fallback follow-up — 2026-10-23

The user's native smoke test proved that the selected Barrier is first in the `PRICE`
subscription, yet no direct quote tick arrives. Diagnose both supported quote templates against
DEMO, configure the official `Pricing` Lightstreamer data adapter for `PRICE`, retain the exact
selected EPIC and never substitute the chart-underlying quote. This is a read-only streaming
change; it creates no broker mutation path.
