# R04 migration preview

## SQLite schema v1

- `schema_migrations(version, applied_at_utc)` records applied versions.
- `journal_events(sequence, event_id, timestamp_utc, event_type, correlation_id, account_ref, instrument_id, payload_json, realized_pnl_amount, realized_pnl_currency, pnl_status)` stores sanitized immutable events.
- Unique event IDs prevent duplicate ingestion.
- SQLite triggers reject `UPDATE` and `DELETE` on `journal_events`; corrections are new events.
- Decimal financial values are stored as canonical text, not binary floating point.

## Migration and recovery

- No database is opened or created at import time.
- Fresh databases receive schema v1 transactionally.
- Before changing a non-empty database version, create a sibling timestamped backup.
- Run `PRAGMA integrity_check` after migration.
- On migration/integrity failure, close the connection and restore the backup; never delete the only copy.
- An unknown newer schema is refused without mutation.

## P&L aggregation

- Aggregate only journal events explicitly marked realized.
- Preserve confirmed, estimated and unknown states separately.
- Use `Decimal`, UTC timestamps and standard-library `zoneinfo` for day/week/month/year grouping.
- Cancelled or non-executed events contribute no realized P&L.

## Settings and workspace

- Preserve the existing JSON configuration and secret exclusions.
- Replace direct writes with temp-file + `os.replace` atomic persistence.
- Add validated, optional main-window geometry and splitter sizes; old files remain loadable.
- Do not introduce docks or redesign the interface in R04.

## External effects

- No dependency installation.
- Tests use temporary directories only.
- Runtime database creation remains opt-in through explicit store construction/initialization.
