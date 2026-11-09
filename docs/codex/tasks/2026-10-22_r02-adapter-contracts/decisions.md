# R02 decisions

- Extend the existing architecture; do not relocate IG modules.
- Domain contracts use only standard-library and existing domain types.
- Capabilities and ambiguous outcomes are explicit values, never inferred as success.
- Provider mappings are keyed by `(provider_id, instrument_id)` and never assume source prices are executable broker prices.
- No production execution adapter is introduced in R02.
