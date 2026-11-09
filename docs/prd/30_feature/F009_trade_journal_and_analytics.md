# F009 — Trade Journal and Analytics

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Feature specification.\
**Last updated:** 2026-10-22


## Goal
Record all trades and decisions, then compute performance metrics to improve rules over time.

## Non-goals
- No tax/accounting module in MVP.

## Requirements
- Store ticket proposals, accepted tickets, pending-order events, position updates, stop/limit changes, exits, PnL, user comments.
- Support tags: instrument, setup type, macro context, manual override, software pending order, dynamic stop mode.
- Store R multiple for each closed trade.
- Compute basic stats: win rate, average win/loss, expectancy, profit factor, max drawdown, result by instrument/setup.
- Export CSV/JSON without secrets.

## Constraints
- Journal event log should be append-only.
- Corrections must be added as events, not overwrite history silently.

## Acceptance criteria
- Every opened/linked trade has an event trail from proposal to close.
- Analytics can run on sample data.
- Export contains no credentials or tokens.

## Testing notes
- Unit-test journal persistence.
- Unit-test metrics on deterministic sample trades.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 13; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-13"></a>

## 13. Historique, recorder et statistiques

**REQ-REC-001/P0** Journal append-only des événements : comptes, signaux produits ou rejetés, stratégies/version, contexte, décisions humain/IA, validations risque, intentions, ordres, confirmations, stops, clôtures, diagnostics critiques.\
**REQ-REC-002/P1** `TradeResearchRecorder` capture caractéristiques de marché au **moment de la décision**, également pour les signaux ignorés ; évite le biais consistant à ne mémoriser que les trades exécutés.\
**REQ-REC-003/P1** Événements persistés dans SQLite WAL avec migrations versionnées ; résilience transactionnelle, audit corrigeable uniquement par nouvel événement. Séries OHLC archivables en Parquet.\
**REQ-REC-004/P1** Calcul net du P&L intégrant frais, spread réalisé, financement, primes et FX selon valeurs connues ; distinguer `realized`, `unrealized`, `estimated` et `unknown`.\
**REQ-REC-005/P1** Agrégation jour, semaine, mois, année et période libre, timezone configurable ; afficher différences entre compte et consolidé, nominal et net.\
**REQ-REC-006/P1** KPIs : gain/perte, win rate, profit factor, expectancy, drawdown, gain/perte moyen, R réalisé, MFE/MAE, durée, horaires, marchés, stratégies, modes et risques IA estimés.\
**REQ-REC-007/P1** Import d'historiques de transactions CSV IG avec mapping validé et déduplication ; imports identifiés distinctement des ordres réels pilotés par l'application.\
**REQ-REC-008/P1** Export pseudonymisé ; aucun token, API key, password, CST/XST, identifiant sensible brut ni clé de notification dans les exports.

**AC-REC-001** Un ordre annulé avant exécution est visible dans le journal, sans faux P&L réalisé.\
**AC-REC-002** Deux trades au cours du même jour, avec frais/FX connus, se retrouvent dans les totaux jour, semaine et mois sans double comptage.\
**AC-REC-003** Après crash, événements persistés permettent de reconstituer les états sans inventer les confirmations broker manquantes.

## V1.2 traceability

[Chapter 4](../10_architecture/overview.md) · [Acceptance matrix](../90_quality/acceptance_matrix.md) · [Definition of Done](../90_quality/definition_of_done.md). Criteria are specifications, not passed test results.

## Partial implementation evidence — 2026-10-23

The GUI Paper session exposes an append-only trail from submitted proposal to simulated fill and
stop/target/KO close, together with read-only Positions, Orders and Journal views. After explicit
human authorization, SQLite schema v2 can save a checksummed full Paper checkpoint and restore the
latest one only through visible user actions. There is no database I/O at startup, no IG identity or
secret in the payload and no broker reconciliation. The complete analytics and import scope of
REQ-REC-001–008 remains incomplete.
