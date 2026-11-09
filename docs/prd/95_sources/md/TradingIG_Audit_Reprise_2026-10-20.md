# TradingIG — Audit du dépôt et plan de reprise

**Date :** 2026-10-20\
**Dépôt :** https://github.com/stephanerey/TradingIG\
**Nature de l'audit :** inspection statique du dépôt connecté à GitHub. Aucune modification de code, aucun test local ou appel authentifié à IG n'ont été effectués.

## 1. Référence Git à retenir

- Branche de base actuelle : `main`, commit `865963f01822fc45dc5fea0d3dc5a9fb89097026`.
- Branche fonctionnelle la plus avancée : `codex/stream-live-candle-robustness`, commit `512c16d59337d2b92bb475daecb96cc902eb00c0`.
- Comparaison : branche avancée **60 commits ahead / 0 behind** `main` ; historique non divergent. Il est possible de promouvoir les travaux par fast-forward après validation.
- Autres branches : `codex/p01-product-discovery-gui` et `codex/install-python-codex-pack`.
- IMPORTANT : ne pas reconstruire l'application sur `main` sans prendre en compte la branche avancée.

## 2. Fonctions effectivement implémentées (branche avancée)

| Sous-système | Fichiers existants | Constat |
|---|---|---|
| REST IG | `adapters/ig_rest.py`, `services/ig_connection_service.py` | Authentification, liste et changement de compte actif, recherche de marchés et récupération d'historique. Toutes les méthodes d'ordre restent désactivées. |
| Streaming IG | `adapters/ig_streaming.py`, `app/streaming_bridge.py` | Lightstreamer PRICE/CHART, signaux Qt, diagnostics CLI. |
| Produits | `services/product_discovery_service.py`, `ui/product_selector.py` | Recherche, classification heuristique, liste filtrable par familles/classes, rapports expurgés. |
| Bougies | `services/candle_aggregation_service.py`, `services/candle_history_service.py` | Fusion REST/stream, bid/mid/ask, séries canoniques et persistance locale JSONL. |
| GUI | `ui/main_window.py`, `ui/chart_view.py`, `ui/settings_dialog.py`, `ui/account_status_widget.py` | PyQt5/PyQtGraph, chandeliers, zoom, curseurs, résolution, source du prix, panneau comptes, produits, paramètres. |
| Secrets et logs | `adapters/credentials.py`, `utils/redaction.py`, `utils/logging_config.py` | Keyring, masquage des secrets, rotation de logs. |
| Tests | `tests/unit/*.py` | 12 fichiers, 102 fonctions explicites `test_...` repérées statiquement. Réussite actuelle non vérifiée. |
| Documentations | `docs/prd/`, `docs/codex/`, `AGENTS.md` | PRD modulaire existant F001–F011, phases P00/P20/P30 et consignes d'agent. À actualiser, pas à dupliquer. |

## 3. Modules non fonctionnels ou incomplets

- `services/risk_engine.py`, `ticket_builder.py`, `trade_manager.py`, `setup_scoring_service.py`, `pending_order_engine.py`, `journal_service.py`, `analytics_service.py`, `macro_context_service.py` restent des squelettes.
- `persistence/sqlite_store.py`, `repositories.py` sont des squelettes ; pas de vraie base transactionnelle ni de statistiques P&L.
- `adapters/news_provider.py` et `economic_calendar.py` sont des squelettes ; la macro-ribbon est principalement statique.
- Pas de moteur d'exécution d'ordres opérationnel ; `IGRestAdapter.create_otc_position`, `update_position`, `close_position`, `create_working_order` lèvent `LiveTradingDisabledError`.
- Pas de multibroker natif, de surveillance multi-compte simultanée ni de trading auto.
- Pas de stratégie opérationnelle, ni indicateurs et sentiment calculés en production, ni backtesting, ML ou LLM intégrés.

## 4. Défauts ou risques identifiés dans le code

**P0 — Corriger avant les indicateurs/ordres**

1. `ui/main_window.py::_load_selected_product_history` teste `_api_allowance_exceeded` **avant** la lecture du cache local : historique déjà disponible inaccessible en cas de blocage REST.
2. `services/candle_aggregation_service.py::apply_chart_update` remplace la bougie d'un bucket par la dernière sous-bougie ; le fallback M1→M5 ne reconstitue pas correctement O/H/L/C sur toutes les minutes. Signalé également dans `docs/codex/tasks/2026-05-12_stream-live-candle-robustness/findings.md`.
3. La logique de récupération historique avec fallback REST est appelée directement depuis `MainWindow`, avec risque de blocage du thread graphique ; des attributs `PriceHistoryWorker` existent, mais le parcours principal reste synchrone.

**P1 — Refactoring ciblé**

4. `ui/main_window.py` ~1 984 lignes et mélange UI, orchestration, cache et REST. Sortir ces responsabilités dans des services ; garder les widgets existants.
5. `CandleHistoryService._persist_closed_candle` est append-only JSONL, sans mécanisme de compaction/idempotence disque ; risque de doublons persistés.
6. `MainWindow._select_account` sauvegarde la valeur demandée même après échec du changement de compte ; synchroniser configuration et compte effectivement actif.
7. Une connexion IG est active à la fois ; le sélecteur existant n'est pas un gestionnaire multi-session. La généralisation doit expliciter les transactions et l'identité du compte.
8. Contrôler la provenance, la fraîcheur, l'horaire et la correspondance entre sous-jacent analysé et produit exécuté.
9. Vérifier la conformité de `requires-python >=3.11` et `ruff.target-version=py312` au runtime Windows retenu.

**Validation encore manquante**

- Pas de nouvelle exécution `pytest`/`ruff` pendant cet audit (accès GitHub lecture seule ; clone réseau indisponible dans le conteneur).
- Pas de test authentifié IG en démo/live ; des documents de diagnostic indiquent « pending manual validation ».
- Couverture précise API IG Barrières/Options pour ouverture, KO, arrêt/protection et modification d'ordres toujours à vérifier sur les comptes cible.

## 5. Décisions fonctionnelles à injecter dans le PRD existant

Toutes les options opérationnelles et les seuils suivants doivent être configurables depuis la GUI, persistés et validés.

- **Plateforme :** Windows uniquement, PyQt5/PyQtGraph, processus capable de fonctionner en permanence GUI ouverte. Architecture assez isolée pour évolutions futures, mais pas de serveur à développer en V1.
- **Modes :** analyse seule ; trading supervisé avec confirmation humaine ; trading automatique, désactivé par défaut et activable après validation.
- **Brokers :** interfaces `BrokerAdapter` et `MarketDataProvider` indépendantes ; IG premier adaptateur, CFD et Barrières/Options ; préparation de l'extension à d'autres courtiers.
- **Données :** historique REST limité + cache local persistant + streaming ; possibilité d'import CSV/Parquet. Ne pas supposer que TradingView offre une API OHLC d'abonné exploitable.
- **Analyse :** principaux indicateurs (EMA/SMA, RSI, MACD, ATR, Bollinger, momentum, niveaux), stratégies trend-following, breakout, pullback, événementielle ; sentiment et confiance IA explicites.
- **Scanner :** scoring par stratégie et consensus ; poids configurables (qualité setup, risque, gain potentiel, sentiment, spread, volatilité) ; colonne « Commentaire / raisons de la décision », mode NO_TRADE.
- **Risque :** 1 % du capital par trade et 3 % de perte quotidienne comme défauts configurables ; calcul P&L net estimé, risque monétaire, risque de marché attribué par IA et exposition. Ces axes doivent être distingués, non additionnés arbitrairement.
- **Limites simultanées :** plafond global de positions et plafond par marché (ex. 1), configurables ; contraintes cumulées multi-comptes et sous-jacents corrélés.
- **Trade Manager :** break-even effectif après frais/spread, mode « sécuriser le trade » (stop avancé en zone de profit après déclenchement configuré), trailing stop, stops monotones et confirmation d'acceptation broker.
- **GUI :** multipanneaux et tabs : scanner ; graphique ; ordres actifs ; historiques/P&L jour-semaine-mois ; comptes ; diagnostics/qualité des données ; paramètres ; alertes et journal.
- **Notifications :** Windows, e-mail, Telegram, smartphone via canaux adaptés ; canaux et événements configurables.
- **IA :** analyse/sentiment, commentaire explicable, enregistrement des décisions et des signaux refusés ; possibilité future de proposer automatiquement des ordres et de demander au moteur d'exécution de les placer dans des limites strictes. IA jamais autorisée à contourner les garde-fous déterministes.

## 6. Architecture cible par incréments

1. `MarketDataProvider` (abstraction) et `IGMarketDataAdapter` existant ; cache/read path indépendant de REST ; validation de bougies et timestamps.
2. `BrokerAdapter` (abstraction) et `IGBrokerAdapter` ; contrats de capacités par compte/produit ; opérations réconciliées.
3. `AccountManager` + `PortfolioRiskService` : états de comptes simultanés ; limites par compte, marché et globales ; événements comptables.
4. `IndicatorEngine` + `MarketRegimeService` + `SentimentService` : déterministes, fenêtre minimale et statuts READY/WARMUP/INVALID.
5. `StrategyRegistry`, `OpportunityScanner`, `ScoringService` ; signaux explicables et horodatés.
6. `TradeResearchRecorder` + journal event-sourced et analytics P&L ; SQLite WAL pour événements, Parquet pour séries si justifié.
7. `TicketBuilder`, `TradeManager`, `OrderExecutionCoordinator` ; mode paper/supervisé d'abord, auto plus tard.
8. `NotificationService` + `DiagnosticsService` ; adaptation des panneaux Qt existants.

## 7. Plan de reprise pour Codex

| Phase | But | Critère de sortie |
|---|---|---|
| R00 | Basculer en sécurité sur la branche avancée ; état Git ; lancer pytest, Ruff et smoke GUI sans secrets | Baseline documentée, aucune perte de code |
| R01 | Corriger 3 défauts critiques OHLC/cache/IO GUI | Tests unitaires avec cas M1→M5, quota REST épuisé, UI non bloquante |
| R02 | Refactorer services et définir adapters génériques sans casser GUI | Tests de contrats avec faux fournisseurs IG/autre broker |
| R03 | Gestion multicomptes + portefeuille + configuration GUI validée | Sessions et ordres isolés, limites 1 %/3 % testées |
| R04 | Persistance, recorder et analytics | Historique d'événements append-only et P&L recomptable |
| R05 | Indicateurs, stratégies, sentiment et scanner explicable | Calcul reproductible, statut invalidité, commentaire et NO_TRADE |
| R06 | Ticket/risk/trade manager en paper puis démo, notifications et onglets | Tests de state-machine, KO, break-even et limites simultanées |
| R07 | Exécution réelle supervisée puis automatique (feature flag) | API IG vérifiée, réconciliation, idempotence et kill switch éprouvés |

## 8. Instruction initiale recommandée pour Codex

> Partir du commit `512c16d59337d2b92bb475daecb96cc902eb00c0` de `codex/stream-live-candle-robustness`. Ne pas réécrire les adaptateurs IG, le chart et les services de bougies existants. Commencer par exécuter et documenter les tests, puis corriger les défauts P0 listés dans cet audit, avec tests de non-régression. Mettre à jour les spécifications existantes sous `docs/prd/`, les conventions `AGENTS.md` et l'état de reprise, en conservant l'historique et en consignant les divergences entre PRD et code. Ne créer aucune voie d'exécution d'ordres live avant la validation de capacité de l'API IG et du Risk Engine. Toute modification doit être faite sur une nouvelle branche dédiée et validée avant fusion.

## 9. Références principales

- https://github.com/stephanerey/TradingIG/tree/codex/stream-live-candle-robustness
- https://github.com/stephanerey/TradingIG/blob/codex/stream-live-candle-robustness/docs/codex/tasks/2026-05-12_stream-live-candle-robustness/findings.md
- https://github.com/stephanerey/TradingIG/blob/codex/stream-live-candle-robustness/docs/prd/PRD.md
- https://github.com/stephanerey/TradingIG/blob/codex/stream-live-candle-robustness/AGENTS.md
