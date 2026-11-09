# Findings

- `AnalysisDirective` deliberately contains no account, quantity, ticket or `OrderIntent`.
- `TicketBuilder` already enforces Paper-only account scope, quote freshness/support and directional
  stop/target/KO geometry.
- A directive technical zone may only be handed off when the current Paper entry is inside it; no
  tolerance or scale conversion is documented, so none is invented.
- Proposal construction is deliberately earlier than the Risk Engine gate: it returns the exact
  `RiskRequest` associated with the immutable ticket but does not evaluate or reserve it.

