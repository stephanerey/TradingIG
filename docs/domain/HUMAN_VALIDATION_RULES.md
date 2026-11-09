# TradingIG human validation rules

- A human must explicitly authorize any future demo or live execution activation; R03 provides none.
- A human selects durable settings precedence and safe configurable bounds when the PRD does not define them.
- Unknown account, FX, exposure, broker capability or ambiguous execution status cannot be human-overridden into an opening.
- Real credentials, account identifiers and broker payloads must not be committed or copied into evidence.
- Any future relaxing of `LiveTradingDisabledError`, global/underlying vetoes or the daily-loss gate requires a separately scoped decision and representative evidence.
- Any destructive or unknown-schema migration, retention deletion, raw-account export or cross-currency consolidation rule requires separate human validation.
- R06 human validation permits only a distinct paper execution boundary. It does not authorize DEMO/LIVE order activation, AUTO mode or relaxing `LiveTradingDisabledError`.
- R07 human validation recorded on 2026-10-22 permits authenticated IG DEMO read-only checks only. It does not authorize creating, updating, cancelling or closing any DEMO order, position or working order, and it never authorizes LIVE access.
- The later 2026-10-23 bounded R07 DEMO mutation authority was consumed by its single CFD probe;
  it does not authorize AUTO or reusable broker execution.
- R08 offline readiness contracts do not activate AUTO. Approved whitelists, quota, acceptance
  evidence and a distinct activation decision remain human-owned prerequisites.
