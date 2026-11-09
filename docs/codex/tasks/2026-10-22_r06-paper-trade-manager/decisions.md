# Decisions

- The R06 adapter is paper-only and structurally separate from `IGRestAdapter`.
- Paper fills are deterministic simulations with declared assumptions, not evidence of broker behavior.
- Risk, data freshness, macro state and expiry are revalidated at trigger time.
- An automatic stop may only preserve or tighten protection; paper confirmation is required before a protected state.
- External notifications, R07 broker capability validation and all live execution remain excluded.
