# Decisions

- Keep provider-specific parsing outside the domain and core services.
- Require explicit usage-rights classification on every source record.
- Store only metadata plus an optional bounded summary when summary use is declared allowed.
- Require every market-context flag to cite normalized source record IDs.
- Degrade unknown-rights evidence to gray/unavailable instead of treating it as usable context.
