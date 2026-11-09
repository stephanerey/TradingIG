# F005 — Macro / News Context Engine

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-11-04


## Goal
Provide a market-context panel that summarizes macroeconomic and geopolitical drivers likely to affect index and gold trades.

## Non-goals
- The module must not automatically trade based only on news.
- The module must not scrape restricted/paywalled sources without permission.

## Requirements
- Track scheduled macro events: Fed/FOMC, ECB where relevant, CPI, jobs reports, GDP, PMI, central-bank speeches.
- Track broad risk context: geopolitical tension, Middle East headlines, oil shocks, dollar index, US yields, VIX/risk sentiment where providers are available.
- Display upcoming high-impact events and time-to-event.
- Display current context summary: risk-on, risk-off, gold-supportive, dollar/yield pressure, event-risk warning.
- Attach source, timestamp, and confidence/status to each context item.
- Produce risk flags used by scanner/ticket builder, e.g. `HIGH_EVENT_RISK`, `GAP_RISK`, `NEWS_DRIVEN_MARKET`.
- Produce a normalized `MacroRibbonState` consumed by the Global Market Context Ribbon.
- For each context item, output: severity (`GREEN`/`YELLOW`/`RED`/`GRAY`), short label, summary, source, timestamp, confidence, and freshness.
- Compute aggregate status: global regime, index bias, gold bias, and event risk.

## Constraints
- Provider selection is configurable.
- Do not store copyrighted full articles; store metadata, summary, URL, timestamp, and tags.
- Context must be clearly separated from trade recommendation.

## Acceptance criteria
- User can see upcoming high-impact macro events.
- Scanner can display macro flags next to technical score.
- News provider failures degrade gracefully.

## Testing notes
- Mock calendar/news providers.
- Unit-test context classification from structured events.

## Related UI
See `F011_global_market_context_ribbon.md` for the persistent red/yellow/green status band shown below the menu bar.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 11; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-11"></a>

## 11. Analyse macro, sentiment et IA

### 11.1 Informations à produire

- Événements : calendrier économique, banques centrales, inflation/emploi, pétrole/OPEP, annonces politiques, tensions géopolitiques ; avec **source et date de publication**.
- Sentiment **directionnel** par sous-jacent : `bullish`, `neutral`, `bearish`, `unknown` ; **risque événementiel** séparé `low/medium/high/unknown` ; **confiance** et **fraîcheur** séparées.
- Macro Ribbon globale persistante : régime `risk-on/neutral/risk-off`, indices, or, pétrole, USD/taux, volatilité, prochaines annonces, état des sources.
- Affichage d'une justification lisible et des raisons déterministes de veto ; aucun texte LLM présenté comme source de vérité broker.

**REQ-AI-001/P1** `NewsProvider` et `EconomicCalendarProvider` abstraits, avec droits d'utilisation documentés, timestamp, URL/source, catégories de marchés et qualité de la donnée.\
**REQ-AI-002/P1** Normaliser un `MarketContextSnapshot` versionné et lié aux signaux et tickets pour replay et audit.\
**REQ-AI-003/P1** Permettre un modèle LLM externe ou local à terme, interchangeable ; sortie JSON typée validée, avec fallback neutre explicite en cas d'erreur.\
**REQ-AI-004/P1** Risque de marché IA et risque monétaire calculé affichés côte à côte ; un désaccord augmente les avertissements, sans autoriser de dépassement financier.\
**REQ-AI-005/P1** Toute analyse a un `model_id`, version du prompt, sources, timestamp, durée de validité et niveau de confiance déclaré ; rien ne justifie de deviner une actualité manquante.\
**REQ-AI-006/P2** Prévoir une sélection/suggestion automatique de stratégie selon régime, validée hors échantillon ; l'exécution passe toujours par le même Risk Engine.\
**REQ-AI-007/P2** Aucun fine-tuning LLM sur l'historique court des seuls trades exécutés comme condition préalable. Comparer d'abord analyse statistique et ML tabulaire (ex. gradient boosting), avec contrôle du biais de sélection.\
**REQ-AI-008/P2** Activer l'exécution initiée par l'IA uniquement sous `AUTO`, sur comptes et stratégies autorisés, avec quota, kill switch, contrôle d'expiration, journal et possibilité d'arrêt immédiat.

## Implementation evidence — R05-AI1 (2026-10-23)

- `MarketContextSnapshot` and `MarketAIAnalysis` are versioned, typed and provider-independent.
- Provider output is restricted to directional context, event risk, confidence, explanation, risk
  flags and explicit references to active `MacroRibbonState` signals.
- Model ID, prompt version, source IDs, generation time, validity and confidence are retained.
- Missing providers, provider errors and invalid/untraceable output degrade to explicit
  `UNAVAILABLE/UNKNOWN`; deterministic context remains available and no favorable state is guessed.
- The provider contract contains no technical-indicator calculation, ticket, risk reservation or
  broker command.

This is an offline contract boundary only. No news/calendar provider, local or external LLM,
network call, scanner integration or execution authorization is configured by this evidence.

### R05-CTX1 source normalization (2026-10-23)

The source side now has provider-neutral `MacroEvent`, `NewsItem` and `MarketContextFlag` contracts,
news/calendar protocols and deterministic source-lineage validation. Unknown usage rights degrade
to gray/unavailable and stale output remains handled by `MacroContextService`. These are synthetic
offline contracts only; provider selection, payload mapping and refresh orchestration remain open.

### R05-SRC1 official automated feeds (2026-11-04)

Official Federal Reserve monetary-policy and ECB press/news RSS metadata can now be collected with
bounded standard-library adapters and explicit unavailable health. This does not yet schedule
refreshes, update the Qt ribbon, classify headline impact or call an LLM.

### R05-SRC2 non-blocking source-health refresh (2026-11-04)

Fed/ECB collection now runs outside the Qt event loop at startup, every 15 minutes and on explicit
request. The ribbon displays only source availability. This signal has no score, confidence or
directional/event tags, so it cannot improve regime, index, gold or event-risk aggregates. Headline
assessment, structured macro events, market proxies, scanner linkage and an AI provider remain
open.

### R05-AI2 concrete OpenAI boundary (2026-11-04)

An optional OpenAI Responses adapter now serializes normalized context only and requests the exact
typed output through strict JSON Schema. The official endpoint is pinned, redirects are refused,
request/response sizes and timeout are bounded, `store` is false, and secrets redact themselves.
Refusals, incomplete/ambiguous output and transport/schema failures remain unavailable/unknown.
No model default, API key persistence, web-search tool, live call, runtime activation, scanner
weight or execution path is included. The implementation follows the official
[Responses text-generation guidance](https://developers.openai.com/api/docs/guides/text) and
[Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

The validation probe is also exposed in Settings > OpenAI. The tab reports only whether the
process can see `OPENAI_API_KEY`, requires an explicit model and cost/metadata acknowledgement,
and runs the synthetic request outside the Qt event loop. Success validates only the provider
boundary; it does not activate the scanner, recommend a trade or contact IG.

### R05-AI3 manual consultative runtime (2026-11-04)

After a successful Settings probe in the same process, an explicit Tools action can submit at most
20 metadata-only official Fed/ECB headlines to the validated provider. These records are projected
as gray `ai_evidence`: they are eligible for model citation but have no deterministic score,
confidence, severity or aggregate effect. The bounded call runs in a Qt worker and its typed
direction/event-risk/confidence/source/expiry output appears in a separate consultative ribbon chip.
There is no automatic call, arbitrary web search, article body, scanner weight, ticket or broker
path. The user validated an available `openai-responses:gpt-6-luna` result on 2026-11-05; the
returned directional and event-risk states remained conservatively `unknown`.

### R05-AI4 consented periodic context runtime (2026-11-05)

Settings now separates the one-call synthetic probe acknowledgement from a non-persisted consent
to analyze the eligible official context every 15 minutes for the current process. The timer starts
only after an available structured probe response, waits one full interval before its first real
context call, skips cycles without eligible `ai_evidence` or while another call is active, and
continues to use the existing Qt worker. The request contains only the normalized official evidence
and selected epic; account, ticket, position and order state remain outside the provider boundary.

This periodic result is still consultative. The longer-term product direction may combine typed AI
context, market summaries and deterministic indicators into an execution **intent**, but REQ-AI-008
still requires a separately activated `AUTO` policy, authorized account/product/strategy, freshness,
quota, deterministic Risk Engine approval, kill switch, reconciliation and journal before any broker
command. The AI result alone can never authorize an order or override a veto.

### R05-CTX2 structured scheduled-event risk (2026-11-05)

Normalized macro events explicitly marked `HIGH` can now be projected into traceable red event-risk
flags within caller-supplied pre/post windows. The projection is non-directional, retains exact
source-record lineage and time-to-event, and reuses the existing rights/freshness degradation. No
importance is inferred from text, no default window is hidden, and no concrete calendar provider,
network call, ticket or execution path is added.

### R05-CAL1 Trading Economics calendar boundary (2026-11-05)

The chosen Trading Economics provider now has an injectable, bounded standard-library adapter.
It validates the provider schema and maps only explicitly configured categories; provider timing
precision and source lineage are retained. Unknown subscription rights deliberately degrade event
risk to gray. The adapter has only synthetic offline evidence: no real key or request, automatic
refresh, GUI status, scanner weight, ticket or execution path is enabled.

### R05-CAL2 session-gated calendar runtime (2026-11-05)

The desktop now exposes a masked-key Trading Economics validation tab. Explicit countries,
lookahead and event-risk windows are submitted in a worker thread; a successful probe enables a
15-minute refresh only for the current process. Calendar health/event signals and official news
are recomposed together. No key is currently present, so real availability remains unvalidated;
unknown usage rights still prevent a favorable or red deterministic event-risk aggregate.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.
