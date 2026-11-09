# Codebase Findings

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.


**Last updated:** 2026-10-22

## Findings
- <...>

## Debt list
- <...>

## Notes
- <...>

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 3; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-3"></a>

## 3. Baseline vérifiée du dépôt et stratégie de reprise

### 3.1 Historique Git

- `main` : `865963f...`, P00 bootstrap + PRD modulaire.
- `codex/stream-live-candle-robustness` : `512c16d...`, **60 commits en avance, aucun commit en retard** à la date de l'audit. Fusion *fast-forward* possible **après validation locale** ; travailler initialement sur une **nouvelle branche** dérivée de la branche avancée.
- Ne supprimer aucune documentation sous `docs/prd/`. Mettre à jour les fichiers existants (`PRD.md`, F001–F011, architecture, décisions, phases), ne pas créer deux sources normatives concurrentes.

### 3.2 Matrice code réel / cible

| Périmètre | Baseline `512c16d` | Travaux attendus |
|---|---|---|
| IG REST et comptes | Auth, listes, changement du compte actif, historique, découverte | Généralisation `BrokerAdapter` / sessions, réconciliation et capacités |
| IG streaming | Lightstreamer PRICE/CHART et bridge Qt | Health, watchdog, souscriptions stables, consommation par plusieurs marchés |
| OHLC | REST + cache historique + cache stream JSONL, Bid/Mid/Ask | Agrégation M1→N correcte, qualité, unification et quotas |
| GUI | Fenêtre principale, graphe, produits, settings, bandeau comptes | Docks/tabs, scanner, positions, ordres, historique, P&L, diagnostic |
| Macro ribbon | Widget statique | Vrais signaux, sentiment, provenance/fraîcheur |
| Risque, ticket, trade manager | Principalement squelettes | Implémentation déterministe testée |
| Stockage métier | Squelettes SQLite | Migrations, journaux append-only, transactions, stats |
| Stratégies, scanner, IA | Squelettes ou documentation | Moteurs nouveaux et contrats explicites |
| Exécution | **Désactivée** par `LiveTradingDisabledError` | Paper, démo validée, supervisé, puis auto |
| Tests | 12 fichiers de tests unitaires, 102 fonctions `test_*` détectées statiquement | Baseline `pytest`/Ruff, tests de non-régression, intégration/replay |

### 3.3 Anomalies prioritaires héritées

- **BUG-DATA-001 / P0** — Le flag global `_api_allowance_exceeded` est testé dans `MainWindow._load_selected_product_history()` **avant** la lecture du cache streaming ; corriger pour permettre l'accès local sans REST.
- **BUG-DATA-002 / P0** — Fallback M1→M5 : `CandleAggregationService.apply_chart_update()` remplace un bucket par la dernière sous-bougie au lieu d'agréger correctement open premier, high maximal, low minimal, close dernier.
- **BUG-UI-003 / P0** — Des requêtes REST historiques avec fallback peuvent être appelées depuis le chemin principal de la fenêtre ; déplacer les appels bloquants hors thread GUI.
- **BUG-DATA-004 / P1** — Le cache JSONL append-only peut contenir plusieurs versions d'une même bougie ; ajouter compaction/idempotence et tests de récupération.
- **BUG-ACC-005 / P1** — Après échec de changement de compte, `MainWindow._select_account()` peut persister un identifiant non effectivement actif ; ne sauvegarder que l'état confirmé.
- **DEBT-UI-006 / P1** — `main_window.py` ≈1 984 lignes, mélange GUI/REST/cache/orchestration ; extraire par petites PR vérifiées.
- **RISK-QUAL-007 / P0** — Il n'y a pas encore de réexécution locale des tests ni de validation authentifiée des capacités Barrières/Options IG ; ne pas présumer leur fonctionnement.

### 3.4 Règles anti-régression

**REQ-BASE-001/P0** Codex doit noter la branche, le commit, le statut Git, l'environnement Python et le résultat `pytest`/`ruff` **avant** toute modification.\
**REQ-BASE-002/P0** Les adaptateurs IG, les modèles et les widgets existants sont conservés jusqu'à refactoring justifié par tests.\
**REQ-BASE-003/P0** Chaque phase part d'une branche isolée, modifie une responsabilité identifiable et expose un rapport de diff, tests, limites restantes.\
**REQ-BASE-004/P0** Interdiction d'introduire un chemin de trading réel dans la phase de reprise/fiabilisation.

## Source erratum and current evidence boundary

Chapter 3 calls the GUI I/O issue BUG-UI-003, while chapter 18 calls it BUG-DATA-003. Both refer to the slow historical REST path; retain the source text and use BUG-UI-003 when tracing that finding. This is a source-label discrepancy, not a second confirmed bug. None of the historical findings has been reproduced during this documentation-only task.
