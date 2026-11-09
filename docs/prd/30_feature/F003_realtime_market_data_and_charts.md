# F003 — Real-time Market Data and IG-like Charts

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


## Goal
Display a candlestick chart close enough to the IG web platform workflow to support the user's manual decision process and trade monitoring.

## Non-goals
- Do not clone the full IG platform.
- Do not implement advanced drawing tools in MVP unless trivial.

## Requirements
- Load historical candles via REST.
- Update live price via Streaming API.
- Support at least 5 min, 1 h, and configurable timeframes.
- Display candlesticks with OHLC tooltip/crosshair.
- Display bid/ask/current price labels.
- Overlay entry, stop, limit, KO/barrier, R/R label, software pending trigger, and PnL markers.
- Display open position markers and current state (`OPEN`, `PROTECTED`, `TRAILING`).
- Coexist with a persistent Global Market Context Ribbon above the chart workspace; chart area should resize cleanly when the ribbon is visible.
- Detect and display stale data.

## Constraints
- Chart rendering must remain responsive during streaming updates.
- Candle aggregation must be deterministic and testable.

## Acceptance criteria
- Chart can reproduce the essential visual workflow seen in IG screenshots: candles + horizontal lines for KO/stop/limit/entry + labels.
- Stale feed warning appears when no update is received beyond threshold.
- Chart can run from replay data without IG.

## Testing notes
- Unit-test candle aggregation.
- Replay known sessions and compare overlay levels.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 6; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-6"></a>

## 6. Données de marché et OHLC

### 6.1 Sources et politique d'accès

- Source initiale : REST et Lightstreamer IG ; historique d'abord depuis le cache local, puis backfill **ciblé** si nécessaire, streaming en continu.
- Sources futures : adapters de données autorisés, CSV et Parquet ; aucune dépendance bloquante à TradingView. Des webhooks TradingView pourraient être évalués ultérieurement comme événements, non comme OHLC garanti.
- Respecter les quotas contractuels du fournisseur : scheduler central, priorités, consolidation des demandes, cache, backoff et état visible. Éviter les réessais à grande fréquence après réponse de quota épuisé.
- Quand un fournisseur d'historique est indisponible, l'application démarre avec l'historique local et marque les indicateurs insuffisamment initialisés.

### 6.2 Modèle canonique

`Candle` comprend : `instrument_id`, `provider_id`, `source_symbol`, `timeframe`, `start_utc`, `end_utc`, `price_basis` (BID/MID/ASK), `open/high/low/close`, `volume?`, `closed`, `revision`, `quality_state` et `provenance`. Interdiction de mélanger des bases de prix ou des instruments dont la correspondance n'est pas vérifiée.

**REQ-DATA-001/P0** Validations : `high >= max(open, close)`, `low <= min(open, close)`, timestamp strictement cohérent, OHLC numériques, absence de duplicats logiques, métadonnées de source.\
**REQ-DATA-002/P0** Agrégation exacte : pour M1→M5, `open=O` de la première sous-bougie, `high=max(H)`, `low=min(L)`, `close=C` de la dernière sous-bougie, volume somme si sémantique connue ; une bougie incomplète reste marquée `PARTIAL`.\
**REQ-DATA-003/P0** Ne pas fabriquer de bougies sur les périodes de marché fermé ou de déconnexion non reconstruite ; représenter gaps et indisponibilité.\
**REQ-DATA-004/P0** Priorité de lecture : cache local → éventuel backfill REST → mise à jour streaming ; quota REST ne bloque jamais la lecture locale.\
**REQ-DATA-005/P0** Transférer toute I/O réseau et lecture disque potentiellement lente hors thread Qt principal ; mise à jour GUI uniquement par événements/signaux.\
**REQ-DATA-006/P0** Détecter flux `LIVE`, `STALE`, `RECONNECTING`, `FAILED`, `UNKNOWN` et dernière mise à jour ; blocage des nouvelles entrées dépendant de prix périmés.\
**REQ-DATA-007/P1** Synchroniser après reconnexion, détecter trous, rejouer les bougies corrigées en ordre temporel ; ne pas compter les données récupérées deux fois.\
**REQ-DATA-008/P1** Cache persistant idempotent, écriture atomique, index par symbole/timeframe/base ; SQLite WAL initialement et Parquet pour l'archive colonne si volume justifié. Migrer les JSONL existants sans perte.\
**REQ-DATA-009/P1** Planification du backfill : budget par provider/compte, démarrage rapide, priorité quotes/positions/ordres, warmup de chaque indicateur ; pas de scans massifs automatiques d'instruments inconnus.\
**REQ-DATA-010/P1** Indicateurs dotés d'un état `READY`, `WARMING_UP`, `INVALID`, avec nombre de bougies disponibles/requises et cause détaillée.\
**REQ-DATA-011/P1** Import CSV/Parquet avec validation des colonnes, de la timezone, des unités et de la provenance.\
**REQ-DATA-012/P1** Visualiser bid/ask, spread et source d'exécution distincte de la source analytique.

### 6.3 Timeframes et conventions

- Graphique principal configurable, défaut M5 ; M1, M5, M15, H1 disponibles, H4/D1 comme contexte.
- Toutes les dates stockées UTC, affichage local configurable (défaut Europe/Paris), calendrier de marché et changement DST gérés explicitement.
- Toute stratégie indique ses dépendances d'historique et sa durée de validité ; pas de signal automatique sur une valeur interpolée silencieusement.

### Session-only multi-market streaming evidence — 2026-11-05

The current human-approved runtime policy temporarily supersedes historical REST/cache warmup:
only M1 updates received during the process are retained, and higher timeframes are aggregated
locally. The Lightstreamer adapter can now place several exact reference EPICs in one chart
subscription, deduplicate them, avoid recreating an unchanged subscription and recover each update
identity from its exact `CHART` item. An update outside the subscribed set is rejected. A separate
in-memory router keeps environment/account/reference series isolated. The provisional Qt runtime
now subscribes the five approved reference markets and prepends the selected product's exact chart
source when different, for a hard maximum of six items. Background updates only feed session
series; the visible chart still renders its selected source exclusively. No REST history, persisted
candle cache, ticket or order path is involved.

If IG rejects the grouped chart subscription with `Insufficient permissions`, the Qt runtime makes
one bounded retry for the selected chart source only. The visible chart can therefore continue
while multi-market Scanner data is explicitly degraded; no repeated probing or automatic order
path is introduced.

If IG also rejects that exact selected `CHART` item while its selected-product `PRICE` stream keeps
updating, the visible chart may accumulate session-only M1 OHLC from those direct quotes. This
fallback retains the product EPIC, is labelled degraded and is not routed to the Scanner as if it
were verified underlying-market data. It does not probe alternate EPICs, read historical REST/cache
or create a ticket/order.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.
