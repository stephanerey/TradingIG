# R02 adapter contracts — task plan

## Objective

Complete only R02 by adding broker/data contracts, explicit capabilities and provider-specific instrument mappings around the existing IG implementation, without moving working modules or enabling execution.

## Scope

- Preserve the existing IG REST/streaming adapters and GUI behavior.
- Add standard-library/domain contract types and a small mapping registry.
- Cover two fake market-data providers, account isolation, unsupported capabilities and ambiguous execution results.
- Keep every real order method hard-blocked.
- Include the requested laptop-window shrink regression.

## Verification

- Focused contract and UI tests.
- Full offline pytest and `ruff check src tests`.
- Offline Qt resize smoke.
- Reference search for old/local adapter protocols and live-trading guards.

## Stop condition

Stop after R02. Do not begin R03/R04 or resolve settings inheritance.
