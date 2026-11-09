# Decisions

- A prior approved review is necessary but never sufficient: execution reevaluates the current
  portfolio snapshot atomically.
- The service does not expose separate authorize and submit steps that could drift.
- Invocation remains an explicit local Paper action; nothing calls it automatically.
