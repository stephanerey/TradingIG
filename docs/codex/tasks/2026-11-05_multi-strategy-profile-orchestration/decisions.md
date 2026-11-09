# Decisions

- A resolved technical profile in the multi-profile path must enable exactly one strategy.
- Strategy IDs are unique within a market input and evaluated in deterministic enum order.
- Existing single-profile inputs remain supported; supplying both modes is invalid.
- All signals are merged before consensus/scoring so divergence is not hidden.

