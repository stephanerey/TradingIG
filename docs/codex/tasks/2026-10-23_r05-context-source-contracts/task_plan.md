# Task plan — R05 context source contracts

## Objective

Add provider-neutral, auditable macro-event, news-item and market-context-flag contracts, then
convert validated flags into the existing `ContextSignal` model without network access.

## Assumptions

- No provider has been selected or authorized yet.
- Provider adapters classify their own payloads into typed records; the core does not infer meaning
  from free text.
- Unknown usage rights or untraceable flags must not become favorable context.

## Smallest sufficient approach

1. Add immutable normalized source records and usage-rights metadata.
2. Define interchangeable news/calendar provider protocols in the existing adapter placeholders.
3. Add a deterministic flag-to-signal normalizer with lineage and freshness checks.
4. Cover Fed/CPI, geopolitical and oil fixtures plus invalid/stale/rights cases.
5. Run targeted lint/tests, protected regressions and the full offline suite.

## Scope

Allowed: offline domain/service/adapter contracts, synthetic tests, API003/F005 documentation.

Forbidden: real provider selection, network, credentials, dependencies, persistence, GUI, strategy
rules, tickets, broker commands, DEMO/LIVE/AUTO.

## Skill

- `codex-tradingig-analysis-scanner`
