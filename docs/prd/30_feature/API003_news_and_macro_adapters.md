# API003 — News and Macro Adapters

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Original text is preserved; documented V1.2 changes govern current scope. No implementation or activation is implied.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-11-04


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

## V1.2 scope alignment

Use typed context/provider contracts, timestamps, rights/licensing and explicit unavailable states. Provider-specific payloads and error mappings remain to be validated.

Canonical requirements: [chapter 11](F005_macro_news_context_engine.md), [chapter 17](../10_architecture/domain_contracts.md), [chapter 20](../01_product/risks_and_assumptions.md).

## Implementation evidence — R05-CTX1 (2026-10-23)

- Provider-neutral immutable `MacroEvent`, `NewsItem` and `MarketContextFlag` contracts exist.
- News and calendar adapter protocols expose normalized records without coupling the core to a
  provider payload.
- Every source record includes stable identity, category, importance, UTC timestamps, source/URL,
  tags and explicit usage-rights status.
- Optional news summaries are bounded and accepted only when declared usage rights allow them.
- Context flags must cite known records, cannot predate their evidence and degrade to gray with no
  score/confidence when any cited source has unknown rights.
- Normalized signals retain source-record lineage and are consumed by the existing conservative
  `MacroContextService` freshness logic.

No real provider, network request, credentials, storage, free-text classifier or provider-specific
payload mapping is implemented by this evidence.

## Implementation evidence — R05-SRC1 (2026-11-04)

- Automated read-only adapters are implemented for the official Federal Reserve monetary-policy
  RSS and ECB press/news RSS, without credentials or a new dependency.
- Retrieval is restricted to configured HTTPS hosts and bounded by timeout, payload size and item
  count; redirects and item links are revalidated.
- Only title, official link, publication/observation time, source and stable ID are retained under
  `METADATA_ONLY`; RSS descriptions/full content are ignored.
- RSS does not provide calibrated market impact, so importance remains `UNKNOWN` and no directional
  or severity inference is made from headlines.
- Network, XML or contract failures become explicit unavailable collection snapshots.
- A bounded live smoke on 2026-11-04 returned 15 normalized items from each source.

The BLS official iCalendar endpoint was researched but excluded: its live automated probe returned
Access Denied with an anti-bot notice. No bypass was attempted. Runtime polling, Qt integration,
persistence and AI/scanner assessment remain outside this evidence.

## Runtime evidence — R05-SRC2 (2026-11-04)

- The desktop composition root injects the Fed and ECB providers; test windows default to no
  provider and therefore perform no network access.
- A `QObject` worker moved to `QThread` collects both feeds outside the GUI event loop.
- Refresh runs at startup, every 15 minutes and through an explicit Tools action.
- The ribbon receives availability only: all available is green, partial availability yellow and
  total failure gray. Score and confidence remain absent.

No title classification, persistence, credential, IG call or execution path is added.

## Provider evidence — R05-CAL1 (2026-11-05)

- Trading Economics was selected by the user as the structured economic-calendar provider.
- The adapter pins the official HTTPS API origin and sends the injected key only in the
  `Authorization` header; credentials are neither persisted nor placed in URLs or errors.
- Countries and known category mappings are explicit. Unmapped categories stay `OTHER` and usage
  rights stay `UNKNOWN` unless the configured subscription rights are separately confirmed.
- UTC windows, timeout, payload size, event count, schema, importance, timing precision, IDs,
  duplicates, content type and redirects are validated before normalization.
- Synthetic fixtures prove composition with the deterministic scheduled-event risk service.

No real Trading Economics request, GUI activation, ticket mutation or broker execution is evidence
of this lot.

## Runtime evidence — R05-CAL2 (2026-11-05)

- Settings exposes key presence only for `TRADING_ECONOMICS_API_KEY`; the value is never rendered,
  persisted or logged.
- Countries, lookahead and pre/post event windows are explicit. A consented manual probe runs in a
  `QThread`; only a successful normalized response activates a 15-minute session timer.
- Calendar availability and scheduled-event flags are composed with official-news signals instead
  of replacing them. Failures become a gray diagnostic without blocking Qt.
- Usage rights remain `UNKNOWN`, so event flags stay gray even when the source is reachable until
  the subscription rights are qualified.

Offline tests are green, but no key was present and no real provider request has been validated.
