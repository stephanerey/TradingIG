# Architecture Overview

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

## Goal
Define a modular desktop application where market connectivity, risk logic, trade management, charting, and UI remain decoupled and testable.

## Non-goals
- Do not put trading rules directly inside UI widget code.
- Do not hardcode IG EPICs or credentials in source code.
- Do not make live execution available before demo validation and explicit user enablement.

## High-level components
```text
[Qt UI]
  ├── Settings / Login View
  ├── Product Selector
  ├── Global Market Context Ribbon
  ├── Market Dashboard / Scanner
  ├── IG-like Candle Chart
  ├── Ticket Builder
  ├── Pending Order Monitor
  ├── Trade Monitor
  └── Journal / Analytics

[Application Services]
  ├── MarketDataService
  ├── ProductDiscoveryService
  ├── SetupScoringService
  ├── MacroContextService
  ├── MacroRibbonService / ViewModel
  ├── RiskEngine
  ├── TicketBuilder
  ├── SoftwarePendingOrderEngine
  ├── TradeManager
  ├── JournalService
  └── AlertService

[Adapters]
  ├── IGRestAdapter
  ├── IGStreamingAdapter
  ├── NewsProviderAdapter(s)
  ├── EconomicCalendarAdapter(s)
  └── CredentialProvider

[Persistence]
  ├── SQLite database
  ├── JSON/YAML non-secret settings
  └── OS keyring for secrets
```

## Constraints
- Core logic MUST be UI-independent.
- All external calls MUST go through adapters.
- All recommendations and trade-state changes MUST emit journal events.
- REST and Streaming sessions MUST expose explicit connection state.

## Acceptance criteria
- Services can be unit-tested without IG or Qt.
- UI subscribes to application events; it does not own domain state.
- Adapter errors are normalized into application-level error objects.

## Testing notes
- Mock adapters for unit tests.
- Integration tests gated behind demo credentials.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 4; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-4"></a>

## 4. Architecture cible

### 4.1 Organisation logique

```text
+---------------------- Windows Qt UI ---------------------------+
| Workspace tabs, docks, charts, scanner, accounts, diagnostics   |
| Settings GUI, trade tickets, alerts, journal and statistics     |
+-----------------------------|----------------------------------+
                              | events / commands (typed)
+-----------------------------v----------------------------------+
| Trading Application / Orchestration                             |
| SessionManager | AccountManager | Scanner | TicketCoordinator   |
| StrategyRegistry | TradeManager | NotificationService          |
+------------+-----------------------+---------------------------+
             |                       |
+------------v-------------+ +-------v--------------------------+
| Market Analysis          | | Execution / Risk                  |
| DataQuality & OHLC       | | PortfolioRiskEngine               |
| Indicators & Regimes     | | OrderCoordinator & Reconciler     |
| Technical + Sentiment    | | BrokerAdapter capabilities        |
+-------------+------------+ +----------+-----------------------+
              |                         |
+-------------v------------+ +----------v-----------------------+
| MarketDataProvider(s)    | | BrokerAdapter(s)                 |
| IG REST/streaming        | | IG CFD / IG Barrières-Options    |
| Import CSV/Parquet       | | PaperBroker / future broker     |
+-------------+------------+ +----------+-----------------------+
              +---------------+---------+
                              |
+-----------------------------v----------------------------------+
| Event & Data Storage: SQLite WAL + history Parquet/JSONL        |
| Recorder / audit / snapshots / research dataset / diagnostics  |
+----------------------------------------------------------------+
```

L'interface et les fournisseurs sont des **adaptateurs** ; le domaine des stratégies, du risque et de la position n'importe ni Qt ni l'implémentation IG. Le fonctionnement continu **avec GUI ouverte** est la cible V1 ; la séparation des couches ne doit pas imposer un service Windows dès le départ.

### 4.2 Modules/domaines obligatoires

| Module cible | Responsabilité principale | Dépendances permises |
|---|---|---|
| `domain/*` | Types canoniques, invariants et événements | Python standard uniquement |
| `adapters/brokers/*` | Contrats et implémentations courtiers | Domain + HTTP/SDK |
| `adapters/market_data/*` | REST, streaming, fichiers, futures sources | Domain + SDK |
| `services/market_data/*` | Agrégation, cache, barres, santé des flux | Interfaces providers + domaine |
| `services/accounts/*` | État multi-comptes, snapshots financiers | Interfaces brokers + storage |
| `services/indicators/*` | Indicateurs et calculs multi-timeframes | Bougies validées uniquement |
| `services/strategies/*` | Signaux normalisés et régime de marché | Indicateurs, contexte |
| `services/scoring/*` | Scores et raisons | Signaux, risque estimé |
| `services/ai/*` | Analyse de texte et sentiment avec provenance | Sources autorisées, modèles externes mockables |
| `services/risk/*` | Invariants de risque et autorisation | Comptes, quotes, positions |
| `services/execution/*` | Ordres, réconciliation, états, commandes | BrokerAdapter + RiskEngine |
| `services/trade_management/*` | Break-even, secure, trailing, sorties | Positions, quotes, broker capabilities |
| `persistence/*` | Migrations, journaux, snapshots et séries | Domain ; pas de Qt |
| `ui/*` | Rendu, interactions et validation de formulaire | Application services / view models |

Les nouveaux noms sont **conceptuels** : Codex doit réutiliser les packages actuels et proposer les migrations au cas par cas ; aucun déplacement massif non justifié n'est requis.

### 4.3 Contrats d'architecture

**REQ-ARCH-001/P0** BrokerAdapter indépendant des stratégies ; toutes les commandes reçoivent un `AccountRef` explicite.\
**REQ-ARCH-002/P0** MarketDataProvider indépendant des brokers ; même marché peut être analysé depuis A et négocié chez B avec mapping explicite.\
**REQ-ARCH-003/P0** `InstrumentMapping` : source, identifiant, sous-jacent, devise, type cash/futur/DFB, unité, pas de cotation, horaires, timezone et notion de délai/provenance. Ne jamais présumer qu'un prix source est directement un prix d'exécution.\
**REQ-ARCH-004/P0** `BrokerCapabilities` par environnement/compte/type de produit : découverte, lecture positions, native stops, KO, ordres pending, ouvertures/fermetures, modifications, exécution démo/live. Les fonctions absentes renvoient `UNSUPPORTED`, sans approximation.\
**REQ-ARCH-005/P0** Services de domaine testables sans Qt et sans réseau ; adaptateurs avec mocks/fakes et contract tests.\
**REQ-ARCH-006/P0** Bus événements typés, horodatés en UTC, avec `correlation_id`, `causation_id`, identifiants broker/compte/marché et `schema_version`.\
**REQ-ARCH-007/P1** L'application conserve le GUI ouvert pendant le fonctionnement continu, avec protection contre fermeture accidentelle, état visible du moteur et restauration après crash ; pas de serveur ni service Windows en V1.\
**REQ-ARCH-008/P1** Un mécanisme configuré de redémarrage/auto-reconnexion doit redécouvrir les comptes et les positions **avant** de reprendre les nouvelles entrées.
