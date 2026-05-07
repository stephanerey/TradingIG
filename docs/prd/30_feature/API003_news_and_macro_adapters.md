# API003 — News and Macro Adapters

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Abstract news and macroeconomic data providers so the context engine can operate without coupling to a single source.

## Non-goals
- Do not store full copyrighted articles.
- Do not make unverified claims without source/timestamp.

## Responsibilities
- Fetch upcoming economic calendar events.
- Fetch/ingest market headlines or summaries.
- Fetch optional market proxies: USD index, US yields, oil, VIX/risk proxies if configured.
- Normalize into `MacroEvent`, `NewsItem`, and `MarketContextFlag`.
- Provide timestamps, source, importance, tags, and URL when available.

## Candidate providers
- IG calendar/news if available to the account.
- Public official sources for scheduled events where practical.
- Configurable RSS/API providers.
- Manual import as fallback.

## Constraints
- Respect source licensing.
- Provider failures must not block trading UI; show degraded status.

## Acceptance criteria
- Context panel can be populated from mocked events.
- High-impact events within configured time window raise a risk flag.

## Testing notes
- Unit-test classification: Fed event, CPI, geopolitical headline, oil shock.
