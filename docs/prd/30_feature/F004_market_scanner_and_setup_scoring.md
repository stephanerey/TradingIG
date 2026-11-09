# F004 — Market Scanner and Setup Scoring

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


## Goal
Rank configured instruments and indicate whether a trade is attractive, possible, or should be skipped.

## Non-goals
- No black-box ML in MVP.
- No guarantee of profitability.

## Requirements
- Consume `MacroRibbonState` from the macro context engine so scanner rows can display red/yellow/green macro flags next to technical setup scores.
- Monitor configured instruments: US Tech 100, France 40, Germany 40, Spot Gold.
- Compute technical context: trend, recent impulse, pullback, support/resistance proximity, volatility, relative strength, distance from recent highs/lows.
- Produce a setup score and explanation.
- Explicitly support `NO_TRADE` output.
- Avoid recommending entries that are too extended, too close to KO, or with poor R/R.
- Consider correlation/exposure: avoid stacking multiple similar risk-on/risk-off trades.

## Constraints
- Scores must be explainable and logged.
- Scanner output is advisory and must pass the risk engine before ticket creation.

## Acceptance criteria
- Scanner produces a ranked list with reason codes.
- At least one scenario returns `NO_TRADE`.
- Recommendations can be replayed from historical candle data.

## Testing notes
- Unit-test scoring components.
- Replay screenshots-derived scenarios when data is available.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 7; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-7"></a>

## 7. Analyse technique, stratégies et scanner

### 7.1 Catalogue initial d'indicateurs

**REQ-IND-001/P1** SMA, EMA, RSI, MACD, ATR, Bollinger, momentum/ROC, supports/résistances, niveaux récents, volatilité réalisée, spread et volume/tick volume lorsque signification connue.\
**REQ-IND-002/P1** Tous les paramètres (période, timeframe, activation, visualisation, seuil) éditables GUI, sauvegardés par profil/marché/stratégie.\
**REQ-IND-003/P1** Les indicateurs doivent être calculés dans les services, non dans les widgets ; valeurs numériques reproductibles, testées contre fixtures de référence.\
**REQ-IND-004/P1** Les indicateurs invalides ne peuvent alimenter un signal approuvé pour exécution ; afficher pourquoi.

#### Implementation evidence — R05-IND2 (2026-11-05)

The deterministic indicator service now covers SMA, EMA, RSI, ATR, MACD, Bollinger bands,
momentum, percentage ROC, recent support/resistance, explicitly annualized realized volatility and
a ratio based only on supplied volume/tick-volume. Multi-value outputs retain named components;
all calculations require ordered closed UTC candles and expose warmup/invalid states plus complete
parameter provenance. Spread remains an execution/quote input rather than an OHLC indicator. No
strategy, scanner recommendation, ticket or broker command is produced by this evidence.

### 7.2 Stratégies obligatoires

| Stratégie | Principe initial | Signaux nécessaires | Critères de rejet |
|---|---|---|---|
| `TREND_FOLLOW` | Momentum dans tendance établie | EMA/SMA, pente, confirmation H1/M15 | Tendance contradictoire, signal trop étendu |
| `BREAKOUT` | Rupture d'un niveau confirmé | Résistance/support, ATR, volume/impulsion | Fausse rupture, volatilité ou spread extrême |
| `PULLBACK` | Retour sur zone dans tendance | EMA/structure, RSI, confirmation | Cassure de structure ou perte de tendance |
| `EVENT_DRIVEN` | Événement économique/géopolitique | Horodatage, importance, sentiment, prix post-événement | Source non confirmée, événement ancien, risque de gap |

**REQ-STRAT-001/P1** `StrategyRegistry` permet d'activer plusieurs stratégies sur plusieurs marchés simultanément, sans couplage UI ni broker.\
**REQ-STRAT-002/P1** Signal standard : `signal_id`, `strategy_id/version`, `instrument`, `side` BUY/SELL/FLAT, `generated_at`, `valid_until`, `entry_zone`, `invalidation`, `target`, `features`, `reason_codes`, `confidence_estimate?`, `data_quality`.\
**REQ-STRAT-003/P1** Éviter les données futures : seules les bougies clôturées ou les updates explicitement marqués temps réel sont utilisables selon règles documentées.\
**REQ-STRAT-004/P1** Une stratégie peut produire `NO_TRADE` ; ses exclusions doivent être traçables, pas seulement ses signaux retenus.\
**REQ-STRAT-005/P1** Le mécanisme plugin/configuration est extensible sans modifier le cœur du scanner.

#### Implementation evidence — R05-STRAT1 (2026-11-05)

`TREND_FOLLOW`, `BREAKOUT` and `PULLBACK` now exist as broker-independent configurable engines.
They use only ordered closed candles, emit versioned BUY/SELL/FLAT signals at the candle close,
retain every configured threshold in provenance, and expose explicit warmup, invalid, extension,
volume, volatility, RSI and structure rejection reasons. Entry zones, invalidation and targets are
ATR-based technical hypotheses only. Replay proves future-blind prefix evaluation. No runtime
profile, scanner score, risk approval, ticket or execution path is enabled; `EVENT_DRIVEN` remains
separate because it requires traceable event/context inputs.

#### Implementation evidence — R05-STRAT2 (2026-11-05)

`EVENT_DRIVEN` now conforms to the same versioned signal contract but requires a cited HIGH-impact
event with known usage rights, optional mandatory source URL, a fresh directional assessment that
cites the event ID, and matching post-event price impulse. Excessive gap, missing post-event bars,
unknown rights, stale/future evidence or direction/price disagreement produce explicit FLAT
reasons. Trading Economics events remain non-actionable while their rights are `UNKNOWN`. No
runtime profile, score, ticket or broker command is enabled.

#### Runtime preview evidence — R05-SCAN2 (2026-11-05)

The desktop has an analysis-only `Scanner` tab. On explicit request it converts the current chart
series to an indicator input while always excluding the trailing candle because the chart model
does not prove its closure. It displays the three technical strategy signals, state, rejection
reasons, entry zone, invalidation, target and validity. Initial EMA/RSI/ATR/level parameters are
versioned `scanner-preview-v1-unvalidated` and retained in signal provenance. `EVENT_DRIVEN` is
shown as inactive without qualified context. No partial 0..100 score is manufactured and the view
contains no ticket or order action. Native Windows visual/default-profile validation is pending.

#### Product-context scale decision — 2026-11-05

The human-approved context component uses five explicit states: `CATALYST=100` (dark green),
`ALIGNED=75` (light green), `CAUTION=50` (yellow), `UNFAVORABLE=0` (red), and
`UNKNOWN=unavailable` (gray). `CATALYST` requires a fresh actionable `EVENT_DRIVEN` signal in the
product direction with `EVENT_PRICE_AND_CONTEXT_CONFIRMED` and retained provenance; news or AI
alone cannot create it. A high current event-risk state remains a safety veto. The values are
ranking components, not probabilities or profitability claims.
The same ordinal values and colors apply to all six score components. Component-specific rules
still determine which band is earned; missing evidence always maps to `UNKNOWN`, never to a
favorable band.

#### Shared component evaluators — 2026-11-05

The validated thresholds now have provider/UI-independent evaluators for technical consensus,
conservative reward/risk geometry, execution cost as a percentage of potential gross gain, data
freshness/continuity/quality, and normalized market risk. Divergence, invalid level geometry,
stale/discontinuous data and critical risk retain explicit vetoes. Missing inputs return the
`UNKNOWN` band and therefore prevent `SetupScoringService` from manufacturing a total score.
Settings now persists optional global fee estimates per unit and per side for `CFD/DFB`, Barrier,
Option and Unknown product types. On first display, an explicitly labelled IG France indicative
profile dated 2026-11-05 proposes `0/0.1/0.1/blank`: non-share CFD/DFB commission is zero because
the observed spread is handled separately, while Barrier and Option commission is 0.1 market-
currency unit per contract and side. The operator can clear any value or restore the profile;
share CFDs remain unavailable because percentage/minimum commissions do not fit this flat model.
For a same-epic chart/product only, the runtime execution-cost component combines the
latest session spread with two fee sides and compares that amount with conservative potential gross
gain. If the chart levels come from a different epic (for example a Barrier using its underlying),
the price scale is unverified and the component remains `UNKNOWN`; no cross-scale estimate is made.
The human-approved runtime market-risk proxy remains separate from directional opportunity:
normalized event risk maps `HIGH` to critical/0 with veto, `MEDIUM` to elevated/50, `LOW` to
normal/75, and `UNKNOWN` to unavailable. It never emits the exceptional/100 band without separate
low-risk evidence. Therefore a positive `CATALYST=100` context can coexist with elevated or critical
event risk instead of masking it.
The six PRD default weights (`30/15/20/15/10/10`) and the global Candidate/Watch thresholds
(`75/60`, with Reject below Watch) are now editable and persisted in Settings, then passed into the
runtime scorer. Missing evidence still forces `NO_TRADE` even when an operator assigns zero weight;
weight zero never converts unknown evidence into a favorable value. Account/strategy/market
inheritance remains a later profile extension and is not inferred by this global configuration.
The provisional Scanner table now exposes available component bands per strategy. Missing market
risk or execution cost keeps the total explicitly unavailable and the recommendation `NO_TRADE`.

### 7.3 Score, consensus et commentaires

**REQ-SCAN-001/P1** Scanner tous les marchés configurés ; colonnes : instrument, source/timeframe, signal, stratégie, score, consensus, risque technique, risque IA, gain potentiel net, R/R, spread, état données, **commentaire/raison**, durée de validité.\
**REQ-SCAN-002/P1** Score `0..100`, avec composantes bornées et poids éditables GUI, somme normalisée. **Ce score est un classement, pas une probabilité de gain.**\
**REQ-SCAN-003/P1** Proposition de poids par défaut : setup technique 30 %, sentiment/contexte 15 %, potentiel R/R 20 %, risque marché 15 %, coûts/exécution 10 %, fraîcheur/qualité 10 %. Toute composante indisponible doit être traitée par une règle explicite, jamais transformée en zéro ou valeur favorable sans avertissement.\
**REQ-SCAN-004/P1** Seuils initiaux modifiables : `CANDIDATE >=75`, `WATCH 60..74`, `REJECT <60`; veto de sécurité et `NO_TRADE` priment toujours sur le score.\
**REQ-SCAN-005/P1** Consensus multi-stratégies : chaque score individuel est conservé, divergences BUY/SELL signalées, pondération par stratégie configurable, aucune fusion silencieuse de signaux contradictoires.\
**REQ-SCAN-006/P1** Le champ commentaire explique les facteurs déterminants, critères bloquants, horodatages, provenance et divergence éventuelle sentiment/technique, par texte déterministe au minimum ; l'IA peut produire une explication supplémentaire, clairement étiquetée.\
**REQ-SCAN-007/P1** Classement selon profil d'objectif `balanced`, `risk_minimization`, `profit_potential`, ou pondérations personnalisées ; les règles non négociables de risque restent identiques.\
**REQ-SCAN-008/P1** Sélection d'une ligne → détail des composantes et éventuelle proposition de ticket, sans passer automatiquement un ordre.

#### Multi-market orchestration core — 2026-11-05

A UI- and broker-independent batch service now evaluates multiple product/candle/context inputs in
stable epic order, retains every per-strategy result, and returns one deterministic global ranking.
Stale or invalid market data is isolated as a per-product failure instead of aborting or hiding the
valid markets. Duplicate products and inconsistent product/series identities are rejected. This is
the base for `REQ-SCAN-001`; it is intentionally not yet connected to the provisional table and has
no ticket, broker, order or automatic refresh dependency.
Each market input can also carry a versioned strategy profile selecting any non-empty subset of
`TREND_FOLLOW`, `BREAKOUT` and `PULLBACK` with their full typed configurations. The default profile
is behavior-compatible with the existing preview parameters and remains explicitly unvalidated for
AUTO. This removes the hard-coded runtime registry without inventing new strategy thresholds.

Profile parameters can now be resolved by explicit leaf-level patches in the human-approved
`global -> account -> strategy -> market` order. Every final leaf retains its layer and patch ID;
unknown paths, ambiguous branches and invalid combined configurations are rejected atomically. The
catalog persists values with explicit type tags and exact keys: IG account ID, `StrategyId` and
canonical underlying. Settings preserves it without exposing a provisional editor. The resolver
deliberately does not infer a canonical underlying from an expiring Barrier/Option EPIC; that
relationship is resolved only through the existing explicit `InstrumentMappingRegistry` and an
unmapped provider instrument fails closed. Populating that registry at runtime and the future GUI
remain separate work.

An additional UI-independent preparation boundary now joins each selected IG product to the
multi-market Scanner only through an exact, provenance-bearing product binding: product EPIC,
canonical underlying and reference-price EPIC. It verifies that the session candle series names
the same product and exact reference EPIC, projects the product context, resolves account/strategy/
market profiles, and emits a `MarketScannerInput`. Unknown products or mismatched series fail
closed. It performs no subscription, refresh, ticket, broker or order action; runtime scheduling
and the future GUI remain separate.

A companion session-only candle router can now retain multiple explicit reference markets in the
same process. Each M1 update is accepted only when its exact reference EPIC is product-bound or is
part of the explicit session universe, then shared with every explicitly related product without
duplicating or mixing the canonical observations. Existing conservative M1 aggregation provides
M5/M15/M30/H1 projections; timestamp revisions and environment/account isolation remain intact.
The Qt runtime supplies the five approved baseline references plus the selected exact source when
different, bounded to six items. This service performs no REST history/cache access, ticket or
execution action.

The manual Qt Scanner refresh now assembles the existing multi-market core from discovered products
only when an exact configured product binding exists. It joins the session-only series, normalized
context, account/strategy/market profiles, optional quote spread, configured fee estimate, weights
and thresholds without duplicating those rules in the widget. Missing configured products, warmup
and stale data are isolated per product. Unbound products remain discoverable and Paper-capable but
receive no invented Scanner context. The provisional table still renders only the selected market;
the dedicated ranked-list GUI remains deferred. No scheduler, ticket, broker or order path exists.
The initial canonical underlying vocabulary is restricted to the five human-approved business IDs
`US_TECH_100`, `FRANCE_40`, `GERMANY_40`, `SPOT_GOLD`, and `US_CRUDE`. Persisted aliases and explicit
instrument mappings outside that vocabulary are rejected rather than normalized heuristically.

The multi-market core can now consume one independently resolved single-strategy profile for each
technical strategy on a market. It evaluates the same conservatively closed series per profile,
retains every resolved leaf source on the market item, merges all signals, and only then rebuilds
consensus and scores. Duplicate strategy profiles, mixed legacy/resolved modes, empty selections,
and `EVENT_DRIVEN` injection into this technical engine are rejected. The existing single-profile
input remains compatible.

Product ancestry now has an IG-style lazy navigation contract. One explicitly requested node is
loaded at a time and its ordered IG node breadcrumb is retained. A configured family node maps to
exactly one canonical underlying and one reference-price EPIC, while the tradable Barrier/Option/
CFD keeps its own product EPIC. Missing or competing family nodes fail closed; display names and
EPIC patterns are never used as ancestry heuristics. On the DEMO profile checked on 2026-11-05,
node navigation returned 404 but the lazy IG category path was available and exposed exact
`underlyingName` plus reference EPIC metadata for the five target families. It did not expose a
public derivative-parent relation, so product mapping and the provisional UI remain explicit work.

An additional broker-independent directive core can combine one non-vetoed Scanner result, its
exact strategy signal/consensus and an optional required `MarketAIAnalysis` under a caller-supplied
policy. Direction, confidence, event risk, source scope and expiry are checked deterministically.
Its `READY` output contains only technical levels and evidence provenance: no account, quantity,
ticket, reservation, `OrderIntent` or broker command. It is therefore an analysis handoff, not an
execution authorization.

A separate Paper-only boundary can consume that exact unexpired `READY` directive together with
its Scanner result, an explicit Paper account, quote, quantity and simulation assumptions. Exact
product/signal identity and the current executable Paper entry inside the technical entry zone are
mandatory. The result is only a ticket draft plus its pending risk request; no risk decision,
reservation, fill, position or broker command occurs at this boundary.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Chapter 11](F005_macro_news_context_engine.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.
