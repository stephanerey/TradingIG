# Task plan — R05 official news feeds

## Objective

Add automated read-only ingestion for selected official central-bank RSS feeds without a key or
new dependency, with bounded network behavior and explicit provider-failure degradation.

## Authorized sources

- Federal Reserve Board monetary-policy RSS.
- European Central Bank press/news RSS.

The BLS calendar is excluded from automated ingestion in this lot because the live endpoint denied
the automated probe and displayed an anti-bot policy. No bypass will be attempted.

## Smallest sufficient approach

1. Add a strict, size-bounded RSS 2.0 provider using the Python standard library.
2. Restrict feed and item URLs to configured HTTPS hosts.
3. Store metadata only with stable IDs, UTC publication/observation timestamps and unknown
   importance rather than guessed market impact.
4. Add concrete Fed/BCE provider factories.
5. Add a provider collection snapshot that converts failures into explicit `UNAVAILABLE` state.
6. Verify with synthetic feeds, protected regressions, full offline tests and a bounded live
   read-only source smoke.

## Scope

Allowed: official public read-only RSS, standard-library HTTP/XML, adapter/domain/service code,
synthetic tests and API003/F005 documentation.

Forbidden: credentials, paid providers, BLS bypass, unrestricted web search, scheduling/polling,
GUI calls, persistence, AI classification, strategies, tickets, broker commands, DEMO/LIVE/AUTO.

## Skill

- `codex-tradingig-analysis-scanner`
