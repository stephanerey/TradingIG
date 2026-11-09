---
name: codex-tradingig-storage-audit
description: >-
  Apply TradingIG persistence, journal, P&L and workspace-safety rules when changing SQLite schemas, event recording, analytics, settings or recovery behavior. Use it to preserve append-only audit history, Decimal and UTC semantics, atomic writes, secret exclusion and recoverable non-destructive migrations.
---

# TradingIG storage and audit

Read `references/rules.md` before changing persistence, journal, analytics or workspace settings.

## Non-negotiable boundary

- Never migrate an unknown newer or unversioned non-empty schema.
- Back up before changing an existing database version and restore on failure.
- Keep journal history append-only; corrections are additional events.
- Persist financial values without binary floating-point conversion and timestamps in UTC.
- Reject secrets and raw authentication material from journal payloads and exports.
- Do not create/open the runtime database merely by importing modules.

## Required closure

- Test fresh initialization, append-only enforcement and duplicate IDs.
- Test migration recovery without deleting the only database copy.
- Test reproducible P&L grouping and atomic backward-compatible settings.
- Preserve broker execution guards and use temporary directories for tests.
