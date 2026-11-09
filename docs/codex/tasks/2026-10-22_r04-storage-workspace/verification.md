# Verification

| Check | Result |
|---|---|
| Project domain skills | PASS — 2 skills valid |
| Focused persistence/analytics/config/Qt tests | PASS — 54 tests |
| Full offline suite | PASS — 134 tests |
| `ruff check src tests` | PASS |
| Targeted format check | PASS — 7 storage/journal files |
| RepoMap refresh | PASS |
| SR 4.1 post-install check | PASS — no errors or warnings |

Covered: explicit fresh initialization, schema/WAL validation, unknown-schema refusal, backup restoration after a synthetic migration failure, append-only update/delete triggers, duplicate event IDs, nested-secret rejection, deterministic realized P&L, currency separation, atomic config recovery, workspace round trip and GUI account-switch confirmation.

Limits: no authenticated call, broker order, automatic runtime database creation, destructive migration, CSV/Parquet import, cross-currency consolidation or UI redesign. Named non-UTC IANA zones require timezone data absent from the current Windows Python; unsupported zones fail explicitly.
