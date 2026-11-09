# Findings

- `ticket_view.py` is empty except for a placeholder docstring.
- `ProductSelectorWidget` contains a disabled `Trade - not implemented` button and static ticket text.
- `TicketBuilder` and `RiskEngine` are already deterministic and accept explicit Paper account scope.
- No new dependency, persistent storage or Qt worker is required.
- The preview deliberately uses an isolated, hypothetical empty Paper portfolio; it does not yet consume persisted Paper positions or account settings.
- Native offscreen Qt evidence at 960×600 reports a 0×115 minimum size hint. Selecting the Paper tab hides the product grid and gives the scrollable ticket the available vertical space.
- Native user evidence and sanitized logs showed the selected Barrier first in a successfully
  subscribed `PRICE` group, but zero quote updates while `CHART` continued.
- A bounded DEMO diagnostic reproduced zero `PRICE` ticks with the default data adapter and
  rejected the retired `MARKET` group with Lightstreamer code 21 (`Invalid group`).
- IG's streaming reference declares `Pricing` as the data adapter for `PRICE`; after configuring
  it, the DEMO diagnostic received its first tick and 50 updates in six seconds.
