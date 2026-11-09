# Decisions

- Preserve the existing configuration location and JSON compatibility.
- Use no new dependency; SQLite, Decimal, JSON and timezone handling come from the standard library.
- Keep database initialization explicit and migration recoverable.

- The user validated the local storage/audit skill boundary and schema-v1 recovery preview on 2026-10-22.
- Keep database initialization opt-in; importing or starting the current application does not create the journal database.
- Persist only the existing main-window size and splitter proportions; R04 does not redesign the interface or introduce docks.
- Use UTC when IANA timezone data is unavailable and reject unsupported named zones explicitly; no dependency was added.
