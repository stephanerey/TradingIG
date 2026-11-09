# TradingIG glossary

- **Account reference:** immutable broker/environment/account tuple used to isolate operations.
- **Confirmed account:** account identity explicitly returned by the broker after authentication or a context switch.
- **Economic underlying:** canonical market grouping shared by distinct products or EPICs, such as a CFD and a barrier on the same crude-oil market.
- **Equity basis:** `min(E_ref_day, E_current)` used for the default per-trade budget.
- **Opening reservation:** local, atomic consumption of exposure capacity for an in-flight opening intent.
- **Risk veto:** deterministic refusal that cannot be overridden by UI, script or AI commentary.
- **Reference currency:** currency in which consolidated equity, P&L and financial risk are evaluated.
- **Append-only event:** immutable journal row; a correction is represented by a later event rather than an update or deletion.
- **P&L status:** explicit classification separating realized, unrealized, estimated and unknown financial values.
- **Ranking score:** bounded scanner ordering value; it is not a probability of profit.
- **WARMING_UP:** insufficient closed observations for a reproducible indicator or signal.
- **NO_TRADE:** explicit advisory rejection with recorded reasons; it is not an execution instruction.
- **Macro event:** provider-normalized scheduled economic event with UTC schedule, importance,
  source and explicit usage-rights metadata.
- **News item:** bounded news metadata with publication/observation timestamps; an optional summary
  is retained only when its declared usage rights allow it.
- **Market context flag:** explicit, source-linked assessment projected into a `ContextSignal`; it
  is not inferred from free text by the deterministic core.
- **Paper account:** explicit simulated account scope that cannot route to a broker execution adapter.
- **Paper fill:** deterministic simulated execution with declared spread, fee, slippage and price provenance.
- **Software pending order:** local state machine that observes a configured condition and prepares a paper/manual-confirmation action after full revalidation.
- **Protected trade:** position whose tighter stop has been confirmed by the active execution boundary; a proposal alone is not protection.
