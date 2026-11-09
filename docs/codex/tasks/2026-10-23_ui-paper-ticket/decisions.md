# Decisions

- This lot creates proposals only; it does not call `PaperBroker.execute`, `OrderExecutionCoordinator` or any IG method.
- A quote is fresh only for a bounded interval after it is received by the GUI.
- Barrier previews require a separately entered maximum KO-loss estimate; the UI will not derive it from underlying points.
- Missing canonical underlying mapping is shown as an explicit Paper-preview warning; the product EPIC is used only as a local grouping fallback.
- Do not retain a silent or obsolete `MARKET` fallback. Use the official `Pricing` data adapter
  for `PRICE`; if the exact selected EPIC still emits no tick, keep the ticket disabled.
