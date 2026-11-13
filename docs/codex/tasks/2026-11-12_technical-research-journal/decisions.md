# Decisions

- One immutable event is stored per evaluated strategy signal; scanner preparation/evaluation failures use a separate event type.
- Repeated publication of the same stable signal ID is suppressed against the persistent journal, including across application restarts.
- The raw IG account ID is never stored. A stable environment-scoped SHA-256 prefix is used as `account_ref`.
- Scanner and strategy semantics remain unchanged. The recorder is observational and cannot access broker/order services.
- Persistence failure is surfaced to diagnostics but cannot erase or replace the in-memory scanner analysis.
- Validation export is an explicit CLI action, refuses to overwrite an existing destination and excludes all account and execution data.
- GitHub receives code and documentation only; generated validation bundles are shared separately under human control.

