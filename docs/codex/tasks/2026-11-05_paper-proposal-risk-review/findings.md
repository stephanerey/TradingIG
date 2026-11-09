# Findings

- `RiskEngine.evaluate` is already the non-mutating decision boundary.
- `evaluate_and_reserve` is intentionally excluded because review is not operator authorization.
- Paper submission independently requires authorization and is not imported by this service.
