# Canonical scanner underlyings

## Objective

Replace free-form Scanner market profile selectors with the five human-approved stable business
IDs: `US_TECH_100`, `FRANCE_40`, `GERMANY_40`, `SPOT_GOLD`, and `US_CRUDE`.

## Scope

- Preserve the dirty worktree; no branch, commit, dependency, deletion or external call.
- Use `codex-tradingig-analysis-scanner` and `aurora-architecture-check`.
- Keep provider EPIC mappings explicit through `InstrumentMappingRegistry`.
- Add no GUI editor, broker command, ticket, order or AUTO activation.

## Smallest sufficient approach

1. Add a domain enum for the five approved IDs.
2. Type the persisted catalog and resolver boundary with that enum.
3. Convert only explicit `InstrumentMapping.underlying_id` values and reject unknown values.
4. Update direct consumers, tests and traceability documents.

## Verification

- Typed persistence and resolver tests.
- Protected execution regressions, full suite, Ruff, format and diff checks.

