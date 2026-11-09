# R04 storage and workspace

## Objective

Implement append-only event storage, deterministic P&L aggregation and atomic non-secret settings/workspace persistence without activating broker execution.

## Smallest sufficient approach

- Use Python standard-library SQLite, JSON, Decimal and zoneinfo only.
- Keep existing configuration path and backward-compatible JSON fields.
- Add a versioned schema behind an explicit store initialization call; do not create a database merely by starting/importing the app.
- Back up any non-empty database before a version change and restore it if migration or integrity validation fails.
- Store Qt-independent workspace values; wire only existing main-window geometry/splitter state, without redesigning the UI.

## Exclusions

- No destructive migration, deletion, new dependency, Parquet, CSV import or tax/accounting behavior.
- No real/demo order call and no change to `LiveTradingDisabledError`.

## Method skills

- `aurora-architecture-check` for schema, recovery and consumer closure.
- `aurora-domain-skill-factory` because no current local skill covers append-only financial records.

## Gates

- Human validation of `codex-tradingig-storage-audit` boundary.
- Human authorization of the schema/migration preview before persistence code is added.

## Planned proof

Temp-directory migration/recovery tests, append-only enforcement, reproducible P&L totals, atomic settings/layout round trip, full pytest, Ruff and SR post-check.
