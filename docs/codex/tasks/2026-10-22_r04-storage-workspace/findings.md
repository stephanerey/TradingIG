# Findings

- `sqlite_store.py`, `repositories.py`, `journal.py`, `journal_service.py` and `analytics_service.py` are placeholders.
- Existing JSON configuration excludes secrets but writes directly rather than atomically.
- The current window has no workspace state persistence and no dock architecture.
- No deployed SQLite schema was found, so R04 can start with a guarded v1 schema while refusing unknown databases.
- Windows Python 3.12 in this environment has no IANA timezone database; UTC works from the standard library and unavailable named zones fail explicitly.
- The GUI connection worker had a second account-switch path; it now applies the same explicit confirmation check as the service.
