# Decisions

- Treat “continue” as authority for offline R08 preparation only, not AUTO activation.
- Do not create a default quota, whitelist or approval record because none has human provenance.
- Represent account whitelists by fingerprints so evidence and configuration do not expose raw
  broker account identifiers.
- Bind any future activation to an exact policy digest and runtime generation; restart invalidates
  the activation until reconciliation and a fresh decision.
- Keep current LIVE authority as an unconditional veto.
