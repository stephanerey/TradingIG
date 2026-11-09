---
title: "TradingIG — Product Requirements Document"
subtitle: "PRD V1.1 • Reprise de l’existant & SR Method 4.1.0 pour Codex"
author: "Projet TradingIG"
date: "20 octobre 2026"
lang: fr-FR
---

# TradingIG — PRD V1.1

**Date :** 20 octobre 2026\
**Méthode de développement :** SR Method 4.1.0 (version publiée le 24 septembre 2026), mise à niveau du pack existant requise avant R00\
**Statut :** Spécification produit approuvée pour lancement du développement incrémental ; faisabilité de l'exécution des Barrières/Options IG encore à valider\
**Plateforme cible V1 :** Windows 11, Python, PyQt5, PyQtGraph\
**Dépôt :** <https://github.com/stephanerey/TradingIG>\
**Branche fonctionnelle de référence :** `codex/stream-live-candle-robustness` — commit `512c16d59337d2b92bb475daecb96cc902eb00c0`\
**Branche `main` auditée :** `865963f01822fc45dc5fea0d3dc5a9fb89097026`\
**Destinataire :** Codex, pour implémentation contrôlée par phases\
**Principe :** faire évoluer l'application existante, **ne pas recommencer de zéro**.

> **Note sur la validation :** le code GitHub a fait l'objet d'un audit statique. Les tests Python et les accès IG authentifiés n'ont pas été relancés lors de cet audit. Les éléments qualifiés d'« existants » ne sont donc pas réputés validés en production. Ce PRD est normatif pour les nouvelles fonctionnalités ; les capacités réelles des API externes prévalent sur les hypothèses.

## 0. Mode d'emploi du PRD

- **MUST / Obligatoire :** exigence nécessaire pour accepter la phase concernée.
- **SHOULD / Recommandé :** comportement attendu sauf arbitrage documenté.
- **MAY / Optionnel :** extension permise mais non imposée.
- **P0 :** fondation et sécurité, avant toute exécution réelle. **P1 :** V1 fonctionnelle supervisée. **P2 :** extension progressive / IA quantitative / automatique.
- Les identifiants `REQ-*`, `AC-*`, `ADR-*` sont stables et doivent être repris dans les commits, les tests et le tableau de tâches.
- **Un paramètre fonctionnel mentionné dans ce document doit être modifiable depuis la GUI**, sauf s'il s'agit d'une constante technique intrinsèque ou d'une garde de sécurité non contournable. Il doit être validé, persisté et décrit.

## 1. Vision, objectif et frontières

### 1.1 Vision

Construire une **station locale de trading assisté, supervisé puis automatisé**, capable de surveiller plusieurs marchés, sélectionner et expliquer des opportunités à court terme, préparer des ordres compatibles avec le courtier, gérer les positions et enregistrer toutes les décisions. La plateforme doit rester multi-courtiers par architecture, même si IG est l'unique courtier opérationnel au départ.

**Horizon des trades :** quelques minutes à quelques heures, principalement intraday. Aucun volume minimal de transactions imposé au moteur : `NO_TRADE` est un résultat normal et souhaitable lorsque les conditions sont défavorables.

### 1.2 Objectifs produit

1. Exploiter **IG CFD** et **IG Barrières/Options**, avec une vue consolidée et des contraintes propres à chaque compte/produit.
2. Acquisition OHLC/quotes fiable : **historique initial mesuré + cache local + streaming continu**, indépendante des ordres.
3. Scanner configurable multi-marchés et multi-stratégies, avec score, risque, gain espéré, **commentaire de justification** et statut explicite.
4. Stratégies initiales : **trend following, breakout, pullback et événements** ; indicateurs techniques configurables et contexte/sentiment de marché.
5. Trading en **trois modes** : analyse seule, ordre supervisé, ordre automatique (désactivé par défaut).
6. **Gestion dynamique** : stop, take profit, passage à l'équilibre net, sécurisation de profit, trailing et clôture suivant règles.
7. **Risque paramétrable** : valeurs initiales 1 % par transaction, 3 % de drawdown journalier, 1 position globale et 1 position par sous-jacent, règles tenant compte des expositions sur plusieurs comptes.
8. Interface Windows multipanneaux, onglets, statistiques P&L et diagnostics, fonctionnement continu tant que l'application est ouverte.
9. Recorder de recherche conservant autant les signaux non exécutés que les trades réalisés ; backtest/replay puis validation quantitative des modèles IA.
10. Notifications choisies dans l'interface : Windows, e-mail, Telegram et, indirectement, téléphone via ces canaux.

### 1.3 Hors périmètre de la première livraison utilisable

- Aucun rendement garanti ou objectif de rentabilité contractuel.
- Aucun LLM finement entraîné comme prérequis pour trader.
- Aucun service Windows, déploiement Linux, web app distante ou application mobile native en V1.
- Aucun scrapping de TradingView ou contournement de son mode d'accès aux données ; intégration uniquement via interfaces officiellement utilisables/licenciées.
- Aucune exécution live tant que l'API IG, le contrôle du compte, les tests d'ordres, la réconciliation et les garde-fous n'ont pas été validés.
- Aucun calcul de P&L estimé présenté comme exact s'il manque cours de sortie, taux FX, frais ou financement.

### 1.4 Indicateurs de réussite (mesurables)

- **Intégrité marché :** zéro bougie M5 incorrecte sur la suite de fixtures M1 de référence ; aucun doublon logique OHLC après redémarrage.
- **Sécurité :** zéro ordre réel dans les modes Analyse/Paper ; toutes les commandes sont rattachées à un compte explicite ; aucune réémission automatique après réponse inconnue.
- **Traçabilité :** 100 % des propositions, autorisations, refus, commandes et transitions de position produisent des événements horodatés.
- **Disponibilité :** état de connexion, fraîcheur et capacité des API toujours visibles ; une interruption ne doit pas être masquée comme « connecté ».
- **Qualité des modèles :** toute stratégie/IA est comparée à un baseline hors échantillon, nette de coûts, avant admission au mode automatique.
- **UX :** ouverture des onglets et manipulation du graphique sans bloquer sur une requête réseau ; paramètres persistés et restaurés.

## 2. Décisions fermes et valeurs par défaut

| ID | Décision validée | Valeur initiale / règle |
|---|---|---|
| ADR-001 | Application **Windows uniquement** | Python 3.12 cible à qualifier, PyQt5/PyQtGraph ; GUI ouverte en fonctionnement permanent |
| ADR-002 | Trois modes de trading | `ANALYSIS`, `SUPERVISED`, `AUTO`; démarrage en `ANALYSIS` |
| ADR-003 | IG premier broker, architecture extensible | `BrokerAdapter`, `MarketDataProvider` découplés |
| ADR-004 | Deux types de comptes IG | CFD et Barrières/Options, capables d'être suivis ensemble ; capacités par produit à vérifier |
| ADR-005 | Marchés initiaux | Gold Spot, US Tech 100, France 40, pétrole ; Germany 40 disponible/configurable |
| ADR-006 | Stratégies | Trend, breakout, pullback, événements ; indicateurs et sentiment configurables |
| ADR-007 | Durée des trades | Minutes à heures ; M1/M5/M15, contexte H1/H4 |
| ADR-008 | Risque maximal par trade | **1 %** par défaut, paramétrable par compte ; voir règles conservatrices §8 |
| ADR-009 | Perte/jour | **3 %** de l'equity de référence du début de journée ; blocage des nouvelles ouvertures |
| ADR-010 | Positions simultanées | **1 globale et 1 par sous-jacent** au défaut, deux contraintes indépendantes |
| ADR-011 | Break-even / sécurisation | Déclenchement proposé à **+1R** ; objectif net après coûts ; seuils paramétrables |
| ADR-012 | Scanner | Score explicable par stratégie et consensus ; poids, filtres et classement configurables |
| ADR-013 | IA | Analyse/recommandation d'abord ; proposition/exécution automatique ensuite, seulement avec contrôles |
| ADR-014 | GUI | Dock/panneaux et tabs, layout persisté, paramètres accessibles GUI |
| ADR-015 | Notifications | Windows + e-mail + Telegram ; activation, catégories et fréquence configurables |
| ADR-016 | Données | Cache historique d'abord, backfill ciblé, streaming, imports fichiers |
| ADR-017 | Données TradingView | Pas de dépendance obligatoire à un abonnement TradingView |
| ADR-018 | Travaux existants | Conserver la branche avancée et refactorer incrémentalement |

Les valeurs ci-dessus sont des **valeurs par défaut, pas des cibles de performance**. Les seuils dérogeant aux garde-fous essentiels imposent une validation visible et un événement d'audit ; certaines contraintes ne sont jamais contournables (compte ambigu, ordre dupliqué, donnée critique périmée, API non prise en charge).

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

## 5. Comptes, sessions et portefeuille

**REQ-ACC-001/P0** Déclarer plusieurs profils (`broker_id`, `environment`, `account_id`, libellé, devise, actif/inactif). Support CFD et Barrières/Options IG.\
**REQ-ACC-002/P0** Afficher simultanément les snapshots des comptes suivis, mais isoler l'identité de chaque commande. L'implémentation peut sérialiser les changements de compte sur une session IG si nécessaire.\
**REQ-ACC-003/P0** Interdire l'exécution d'un ordre si l'API ne confirme pas explicitement le compte cible après changement de contexte. Un compte simplement sélectionné dans la GUI ne constitue pas une preuve.\
**REQ-ACC-004/P0** Consolider P&L, cash/equity, marge et exposition dans une devise de référence configurable. Une conversion FX absente rend le total consolidé `INCOMPLETE` et peut bloquer une nouvelle ouverture.\
**REQ-ACC-005/P0** Une limite globale s'applique à tous les comptes actifs et aux marchés regroupés par sous-jacent économique, non à leurs EPIC distincts.\
**REQ-ACC-006/P1** Historiser snapshots de soldes/positions et écarts entre état local et état broker. Vue compte inclut horodatage et fiabilité.\
**REQ-ACC-007/P1** Permettre d'activer ou exclure chaque compte de l'exécution automatique, indépendamment de sa visibilité.

**Cas d'acceptation ACC :** deux comptes IG affichés ; un changement échoué ne modifie pas le compte effectif ; un ordre vers compte A ne peut être placé sur B ; deux produits du même pétrole comptent comme même marché pour la limite par sous-jacent.

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

## 7. Analyse technique, stratégies et scanner

### 7.1 Catalogue initial d'indicateurs

**REQ-IND-001/P1** SMA, EMA, RSI, MACD, ATR, Bollinger, momentum/ROC, supports/résistances, niveaux récents, volatilité réalisée, spread et volume/tick volume lorsque signification connue.\
**REQ-IND-002/P1** Tous les paramètres (période, timeframe, activation, visualisation, seuil) éditables GUI, sauvegardés par profil/marché/stratégie.\
**REQ-IND-003/P1** Les indicateurs doivent être calculés dans les services, non dans les widgets ; valeurs numériques reproductibles, testées contre fixtures de référence.\
**REQ-IND-004/P1** Les indicateurs invalides ne peuvent alimenter un signal approuvé pour exécution ; afficher pourquoi.

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

### 7.3 Score, consensus et commentaires

**REQ-SCAN-001/P1** Scanner tous les marchés configurés ; colonnes : instrument, source/timeframe, signal, stratégie, score, consensus, risque technique, risque IA, gain potentiel net, R/R, spread, état données, **commentaire/raison**, durée de validité.\
**REQ-SCAN-002/P1** Score `0..100`, avec composantes bornées et poids éditables GUI, somme normalisée. **Ce score est un classement, pas une probabilité de gain.**\
**REQ-SCAN-003/P1** Proposition de poids par défaut : setup technique 30 %, sentiment/contexte 15 %, potentiel R/R 20 %, risque marché 15 %, coûts/exécution 10 %, fraîcheur/qualité 10 %. Toute composante indisponible doit être traitée par une règle explicite, jamais transformée en zéro ou valeur favorable sans avertissement.\
**REQ-SCAN-004/P1** Seuils initiaux modifiables : `CANDIDATE >=75`, `WATCH 60..74`, `REJECT <60`; veto de sécurité et `NO_TRADE` priment toujours sur le score.\
**REQ-SCAN-005/P1** Consensus multi-stratégies : chaque score individuel est conservé, divergences BUY/SELL signalées, pondération par stratégie configurable, aucune fusion silencieuse de signaux contradictoires.\
**REQ-SCAN-006/P1** Le champ commentaire explique les facteurs déterminants, critères bloquants, horodatages, provenance et divergence éventuelle sentiment/technique, par texte déterministe au minimum ; l'IA peut produire une explication supplémentaire, clairement étiquetée.\
**REQ-SCAN-007/P1** Classement selon profil d'objectif `balanced`, `risk_minimization`, `profit_potential`, ou pondérations personnalisées ; les règles non négociables de risque restent identiques.\
**REQ-SCAN-008/P1** Sélection d'une ligne → détail des composantes et éventuelle proposition de ticket, sans passer automatiquement un ordre.

## 8. Moteur de risque et dimensionnement

### 8.1 Définitions et invariants

Définir `E_ref_day` = equity de référence au début de la journée configurée (horodatage/currency explicites) ; `E_current` = equity courante fiable ; `E_basis` = `min(E_ref_day, E_current)` par défaut. Le budget par trade est `B_trade = E_basis × 0,01` par défaut. Le seuil de perte journalière est `L_day = E_ref_day × 0,03`. L'interface doit permettre d'ajuster pourcentage, devise de référence, période, règles d'exposition et seuils **dans des bornes sûres**.

**Important :** pour un CFD sans stop garanti, aucune borne de perte absolue ne peut être déduite d'un simple stop logiciel. Les limites représentent des seuils de décision avec scénarios d'écart/gap, non une garantie contractuelle.

**REQ-RISK-001/P0** Vérifier les limites **par compte, globales et par sous-jacent** sur toutes les positions ouvertes, pending réservés et ouvertures en cours. Le contrôle doit être atomique au regard des ordres concurrents.\
**REQ-RISK-002/P0** Refuser une ouverture si sa perte **au stop estimée nette**, majorée des coûts et du slippage de scénario, dépasse le budget. Pour les barrières, afficher et contrôler séparément le **risque maximum jusqu'au KO/premium** ; politique initiale conservatrice : rejet si perte maximale au KO dépasse également le budget alloué.\
**REQ-RISK-003/P0** Si le minimum négociable, le pas de taille, la conversion FX ou les caractéristiques du contrat empêchent de respecter la limite, proposer `NO_TRADE`, pas un dépassement implicite.\
**REQ-RISK-004/P0** Plafonds initiaux `max_open_global=1` et `max_open_per_underlying=1` (paramétrables) ; le système doit compter aussi les intentions d'ouverture en état in-flight pour éviter les doubles déclenchements.\
**REQ-RISK-005/P0** Lorsqu'une perte quotidienne nette (réalisée + latente, sans double comptage) atteint 3 % du `E_ref_day`, interdire toute **nouvelle ouverture** ; la surveillance, réduction ou clôture de risque restent permises. Afficher compte/marché/devise et état.\
**REQ-RISK-006/P0** Distinguer explicitement trois grandeurs non interchangeables : risque financier calculé par le moteur, niveau de risque de marché estimé (technique et IA), confiance/calibration du modèle IA. Aucune « corrélation » naïve de deux nombres sans méthodologie documentée.\
**REQ-RISK-007/P0** Rejeter compte incertain, données de prix obsolètes, marché fermé, produit non supporté, KO invalide, R/R inférieur au seuil choisi, taille non valide, ordre doublon ou exposition inconnue critique.\
**REQ-RISK-008/P1** Exposition corrélée : classer instruments selon sous-jacent et groupes de risque (indices actions, matières premières, etc.) ; seuil configurable et avertissements/veto selon politique.\
**REQ-RISK-009/P1** Calculer bid/ask réel, taille, marge/premium, commissions, financement probable, conversion FX et impact spread ; distinguer estimations et montants confirmés.\
**REQ-RISK-010/P1** Paramètres risk GUI : valeur, unité, plage valide, héritage global→compte→stratégie→marché, changements audités. Les garde-fous critiques ne peuvent pas être contournés par IA, script ou UI.\
**REQ-RISK-011/P1** Afficher avant validation le risque en euros, en %, scénario au stop, au KO, stress-gap, profit net potentiel et R/R.

### 8.2 Calculs d'exemple et tests

Pour un marché coté en points, avec valeur du point `V` par unité de taille, taille `Q`, coût total anticipé `C` et distance stop `D`, la perte estimée est `Q × V × D + C` **uniquement si** la convention de prix du produit, la devise et le mode d'exécution rendent cette formule applicable. Les options/barrières nécessitent leur formule de contrat validée ; aucune conversion « points sous-jacent = prime barrière » n'est autorisée.

**AC-RISK-001** Un capital de référence de 1 000 EUR produit un budget nominal de 10 EUR à 1 %, avant particularités du produit et des frais.\
**AC-RISK-002** Une position et une intention pending réservée épuisent le plafond global 1 ; la seconde ouverture concurrente est rejetée.\
**AC-RISK-003** Une perte nette journalière de 30 EUR sur equity début de journée de 1 000 EUR bloque les nouvelles entrées et laisse la clôture ouverte.\
**AC-RISK-004** L'IA donne score « faible risque » mais FX ou spread indisponible : le ticket est refusé malgré le score.\
**AC-RISK-005** Deux positions sur le même sous-jacent via CFD et barrière consomment le même plafond de marché.

## 9. Ticket Builder, exécution et ordres conditionnels

### 9.1 Séparation des modes

- `ANALYSIS` : accès lecture/analyse ; **aucun appel de création, mise à jour ni clôture d'ordre** vers le broker, même sur requête IA.
- `SUPERVISED` : signal → proposition → Risk Engine → confirmation humaine visible portant sur **instrument, compte, type de produit, taille, coûts, stop/KO** → commande si API supportée.
- `AUTO` : signal autorisé et non expiré → Risk Engine + capability gate + permissions du compte + limites/kill switch → commande ; journalisation et notifications. Désactivé au démarrage et non disponible avant validation de bout en bout. L'IA n'envoie jamais directement une requête HTTP de trading.
- `PAPER` : environnement d'exécution simulé distinct d'un compte réel, activable depuis n'importe quel mode d'analyse/validation, sans possibilité de fuite d'ordres live.

### 9.2 Commande, idempotence et réconciliation

**REQ-EXEC-001/P0** `OrderIntent` immuable avec identifiant interne unique, compte cible, broker, environnement, produit, paramètres financiers, signal et version de règles.\
**REQ-EXEC-002/P0** Toute commande passe par `RiskEngine` et `OrderExecutionCoordinator` ; aucune UI ni LLM ne peut appeler directement `IGRestAdapter` pour trader.\
**REQ-EXEC-003/P0** Modèle d'états minimal `PROPOSED`, `RISK_CHECKED`, `AWAITING_CONFIRMATION`, `SUBMITTING`, `UNKNOWN`, `BROKER_CONFIRMED`, `OPEN`, `REJECTED`, `CANCELLING`, `CLOSED` ; transitions et erreurs persistées.\
**REQ-EXEC-004/P0** Sur timeout ou réponse ambiguë, état `UNKNOWN`, interrogation de l'état broker et des confirmations avant toute nouvelle soumission ; **ne jamais retenter aveuglément** un ordre susceptible d'avoir été accepté.\
**REQ-EXEC-005/P0** Rapprocher les positions réelles avec l'état local après démarrage, reconnect ou bascule de compte ; ne pas autoriser de nouvelles entrées si la réconciliation critique a échoué.\
**REQ-EXEC-006/P0** Capacité d'ouverture/modification/fermeture Barrières/Options IG soumise à test API représentatif **démo puis compte réel explicitement autorisé**. Si non supportée : mode recommandation/supervisé manuel seulement, jamais contournement.\
**REQ-EXEC-007/P1** Ticket comporte produit/contrat, sens, entrée, taille, stop, take profit, KO/barrière, spread, frais, marge/premium, perte et gain nets estimés, score et commentaire.\
**REQ-EXEC-008/P1** Ordre logiciel différé : états `ARMED`, `TRIGGERED`, `AWAITING_CONFIRMATION`, `EXPIRED`, `CANCELLED`, `SUBMITTED` ; revalidation prix, horaires, compte, signal, risque, quota et état du broker **au déclenchement**, plus cooldown/déduplication.\
**REQ-EXEC-009/P1** Une intention logicielle qui dépend de la GUI active porte une mention explicite « non protégée en cas de coupure/arrêt » ; préférer ordres et stops natifs broker lorsqu'ils existent.\
**REQ-EXEC-010/P1** Paramétrage GUI : mode, confirmations, produits, horaires autorisés, types d'ordres, alertes, prix maximum de déviation, délais d'expiration, limites d'intentions.

## 10. Trade Manager et sécurisation

**REQ-TRADE-001/P1** États `OPEN` → `PROTECTED` → `TRAILING` → `CLOSING` → `CLOSED`, avec transitions monotones et historique.\
**REQ-TRADE-002/P1** Fonction « Sécuriser » : lorsqu'un profit latent franchit un seuil configurable (défaut +1R), proposer ou demander un stop dont le **P&L net théorique à ce niveau** est ≥0, avec coussin configurable ; niveaux calculés selon sens long/short et spécifications du produit.\
**REQ-TRADE-003/P1** Distinguer *break-even du prix*, *break-even net après spread/commissions* et *profit protégé*. Un stop non garanti n'assure pas la réalisation du P&L affiché en cas de gap ou slippage.\
**REQ-TRADE-004/P1** Modes trailing configurables : distance fixe, multiples R, ATR, lows/highs de bougies clôturées, manuel ; pas de resserrement sur chaque tick sans seuil/cooldown.\
**REQ-TRADE-005/P1** Par défaut, **ne jamais élargir** le stop : pour LONG `new_stop >= confirmed_stop`; pour SHORT `new_stop <= confirmed_stop`, sauf procédure manuelle exceptionnelle distincte, explicitement désactivée dans l'automate.\
**REQ-TRADE-006/P1** Un stop n'est déclaré « sécurisé » qu'après confirmation du broker, pas à l'envoi de la requête. Si API ne permet pas la modification, afficher instruction/alerte manuelle.\
**REQ-TRADE-007/P1** Paramétrer gestion du take profit, clôture temporelle, seuil de retournement et prise partielle uniquement pour produits qui la supportent.\
**REQ-TRADE-008/P1** Chaque suggestion/modification indique motif, contexte, frais retenus, ancien niveau, nouveau niveau et confirmation/rejet courtier.\
**REQ-TRADE-009/P1** L'automate conserve les protections en cours en cas de blocage de nouvelles entrées ; réconcilie les niveaux après reconnexion.

**AC-TRADE-001** Une position LONG dont le stop initial est 100 ne peut pas recevoir 99 comme modification automatique.\
**AC-TRADE-002** L'utilisateur voit le P&L net théorique protégé et la mention non garantie.\
**AC-TRADE-003** Un refus API ne produit pas l'état `PROTECTED`.\
**AC-TRADE-004** Une nouvelle quote défavorable n'inverse pas un stop déjà confirmé.

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

## 12. Interface Windows et configuration intégrale

### 12.1 Structure

**REQ-UI-001/P1** `QMainWindow` avec workspace central à onglets et panneaux détachables/dockables (`QDockWidget` ou architecture Qt équivalente), dispositions sauvegardées/restaurées.\
**REQ-UI-002/P1** Bandeau permanent : mode actuel, état moteur, courtier/comptes, equity/exposition, P&L, drawdown quotidien, santé données et macro-ribbon.\
**REQ-UI-003/P1** Onglets centraux et docks :

| Vue | Contenu minimal |
|---|---|
| `Scanner` | Watchlist, scores par stratégie/consensus, risques, profit espéré, **commentaire**, filtres, détail |
| `Graphiques` | Multi-charts OHLC, timeframes, indicateurs, niveaux entrée/KO/stop/TP, position et historique des signaux |
| `Positions ouvertes` | Compte, marché, sens, taille, entrée, P&L live, KO, stop, TP, mode de sécurisation, état broker |
| `Ordres` | Propositions, ordres pending natifs/logiciels, in-flight, confirmations, annulations, refus |
| `Historique / P&L` | Liste filtrable des trades et statistiques jour/semaine/mois/année, réalisé/latent, frais |
| `Comptes` | CFD, Barrières/Options, equity, capital libre, marge/premium, exposition et devise |
| `Sentiment / Macro` | Événements, liens sources, directional bias, risque IA, confiance, fraîcheur |
| `Diagnostics` | REST, streaming, quota, cache, gaps, threads, erreurs, latence, journal technique |
| `Notifications` | Canaux, catégories, destinataires, historique et test non destructif |
| `Paramètres` | Tous les profils et les réglages validés ci-dessous |

**REQ-UI-004/P1** Paramètres via GUI, y compris modes, risque, comptes activés, plafonds de trades, stratégie, indicateurs, scores et pondérations, alertes, données, cache, thèmes, timezones, historique, AI et trailing.\
**REQ-UI-005/P1** Configuration hiérarchique avec origine visible et priorité `global < broker/compte < marché < stratégie` lorsque pertinent ; éviter les héritages implicites ambigus.\
**REQ-UI-006/P1** Contrôles avec validation de plages/units, aide contextuelle, valeurs restaurables, aperçu d'impact, persistance atomique ; les réglages de sécurité prennent effet sans redémarrage quand possible.\
**REQ-UI-007/P1** Toute action d'ordre présente explicitement compte, environnement (démo/live), symbole, taille, perte estimée et nature réelle/simulée.\
**REQ-UI-008/P1** Fonctionnement continu : erreur visuelle persistante en cas de déconnexion, pas de disparition silencieuse de fenêtre avec positions ouvertes ; option explicite de confirmation à la fermeture et avertissement pour ordres logiciels en attente.\
**REQ-UI-009/P1** Export CSV/JSON sécurisé des transactions, statistiques et diagnostics expurgés.

### 12.2 Valeurs UI par défaut

- Mode `ANALYSIS`, compte réel non autorisé à placer des ordres, scanner actif sur watchlist configurée.
- Graphique M5 ; contexte M15/H1 ; choix M1, M15, H4 configurable.
- R/R minimal pour génération d'une proposition : **2.0** par défaut, modifiable. Ne pas présenter un ratio supérieur comme promesse de gain.
- Pondérations et seuils du scanner selon §7.3.
- Risque par transaction 1 %, seuil journalier 3 %, plafond global 1 et marché 1.
- Break-even net à +1R, trailing désactivé jusqu'à paramétrage explicite.
- Notifications Windows activables ; e-mail/Telegram désactivés jusqu'à configuration des destinataires et tests.

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

## 14. Backtesting, paper trading et validation quantitative

**REQ-TEST-001/P1** PaperBroker simule ordres, positions, frais, spread, stop/TP, KO et slippage paramétrés avec les mêmes contrats que le broker réel.\
**REQ-TEST-002/P2** Replay chronologique OHLC/événements sans fuite temporelle, warmup identique à la production ; test et traçabilité du signal à l'exécution.\
**REQ-TEST-003/P2** Backtest avec prix bid/ask lorsque disponibles, horaires de marché, écarts, latence, frais, gaps et contraintes du produit. Précision insuffisante explicitement déclarée, pas de résultat « réaliste » sans données adaptées.\
**REQ-TEST-004/P2** Validation chronologique train/validation/test, walk-forward, comparaison au baseline et intervalles/incertitude lorsque applicables ; éviter optimisation sur le jeu final.\
**REQ-TEST-005/P2** ML et LLM doivent prouver valeur ajoutée hors échantillon en P&L ajusté du risque **et** stabilité (drawdown, performance par régime), avant activation en mode automatique.\
**REQ-TEST-006/P2** Versionner données, features, règles, code/commit et paramètres de chaque expérience.

## 15. Alertes, diagnostics et résilience

### 15.1 Notifications

**REQ-ALERT-001/P1** Routeur configurable : Windows toast, e-mail (SMTP ou provider), Telegram bot ; téléphone via notifications du canal choisi, sans imposer une appli mobile native.\
**REQ-ALERT-002/P1** Catégories : opportunité, signal expiré, pending déclenché, ordre confirmé/rejeté/inconnu, stop sécurisé/non confirmé, limite de perte, problème connexion/quota/qualité, reprise et réconciliation.\
**REQ-ALERT-003/P1** Filtrage par sévérité, canal, plage horaire, fréquence, cooldown et acquittement. Les alertes critiques doivent rester consultables dans l'application même si l'envoi externe échoue.\
**REQ-ALERT-004/P1** Les secrets SMTP/Telegram vont au keyring ; masquage dans logs/tests/config/export.

### 15.2 Diagnostic

**REQ-DIAG-001/P0** Vue complète des connexions IG REST/stream, âge dernière quote/bougie, compte courant, état du cache et quota API ; horodatage clair.\
**REQ-DIAG-002/P1** Mesurer erreurs, latences, reconnections, files workers, pending in-flight, occupation DB, gaps, qualité OHLC, fréquence d'updates, et horloge locale/UTC.\
**REQ-DIAG-003/P1** Journal structuré tournant par taille ou jour, niveaux réglables, `correlation_id`, conservation configurable et option export expurgé.\
**REQ-DIAG-004/P0** **Kill switch** logiciel : interdit immédiatement les nouvelles ouvertures; ne désactive pas la surveillance/gestion des positions. Bouton visible, état persistant, audit.\
**REQ-DIAG-005/P0** Mode « dégradation sûre » en cas de flux obsolète, perte réseau, session expirée, quota épuisé ou résultat ordre inconnu : bloquer nouvelles entrées, afficher l'alerte, réconcilier avant reprise.\
**REQ-DIAG-006/P1** Test de notification et test de connectivité disponibles depuis le GUI sans créer d'ordre réel.

### 15.3 Objectifs non fonctionnels et mesurabilité

Les seuils de performance sont des **cibles initiales à mesurer** sur PC Windows de développement, et non des latences garanties par IG :

| Critère | Cible de validation |
|---|---|
| GUI réactive | Un accès REST lent ne bloque jamais la boucle Qt ; commandes GUI utilisables pendant le chargement |
| Refresh GUI | Rafraîchissement limité/coalescé pour éviter un redraw complet à chaque tick |
| Temps signal → passage Risk Engine | Mesuré et journalisé ; seuil d'alerte configurable, pas de promesse de HFT |
| Crash/restart | Récupération des caches/événements puis réconciliation broker avant ouverture |
| Données invalides | Bloquage contrôlé des nouveaux ordres ; diagnostic explicite |
| Tests | `pytest -q`, `ruff check src tests`, smoke GUI Windows, et suites replay/contract selon phase |
| Confidentialité | Secrets uniquement keyring/en mémoire, masqués partout ailleurs |

## 16. Sécurité, déploiement et exploitation

**REQ-SEC-001/P0** Secrets non stockés en clair dans config YAML/JSON ni dans git ; utiliser Windows Credential Manager via `keyring` ou fournisseur sécurisé équivalent.\
**REQ-SEC-002/P0** Séparer environnement `DEMO` / `LIVE`, profils de clés et identité du compte ; confirmation explicite avant première activation LIVE de chaque compte.\
**REQ-SEC-003/P0** `AUTO` nécessite activation explicite locale, stratégies et marchés autorisés, bornes de risque, kill switch, validation API et absence de défauts critiques ; persistance du paramètre d'autorisation à préciser avec prudence (démarrage sûr).\
**REQ-SEC-004/P1** Packaging Windows reproductible, installation documentée pour Python 3.12 / venv puis livrable exécutable packagé dans une phase ultérieure (ex. PyInstaller, à valider).\
**REQ-SEC-005/P1** Mise à jour DB par migrations testées, backup préalable et stratégie rollback/recovery documentée.\
**REQ-SEC-006/P1** Aucune tâche réseau/IA ne doit pouvoir bloquer la gestion locale des états d'ordres et la lecture des diagnostics ; différencier notifications best-effort et contrôles critiques.

## 17. Contrats d'API/domaines à fournir à Codex

Le code suivant constitue **un contrat conceptuel** : il décrit responsabilités, paramètres et erreurs, sans imposer le nom définitif de chaque classe ni une implémentation prête à coller. Codex doit compléter `Protocol`, Pydantic/dataclasses si retenu, tests de contrat et erreurs normalisées.

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol, Sequence

class TradingMode(str, Enum):
    ANALYSIS = "analysis"
    SUPERVISED = "supervised"
    AUTO = "auto"

@dataclass(frozen=True)
class AccountRef:
    broker_id: str
    environment: str          # demo / live / paper
    account_id: str

@dataclass(frozen=True)
class BrokerCapabilities:
    read_positions: bool
    place_orders: bool
    modify_stops: bool
    close_positions: bool
    native_pending_orders: bool
    barrier_knockouts: bool

@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    account: AccountRef
    product_id: str
    underlying_id: str
    direction: str            # BUY / SELL
    quantity: Decimal
    requested_stop: Decimal | None
    requested_target: Decimal | None
    requested_ko: Decimal | None
    signal_id: str | None
    expires_at_utc: datetime

class BrokerAdapter(Protocol):
    def capabilities(self, account: AccountRef, product_id: str) -> BrokerCapabilities: ...
    def accounts(self) -> Sequence[AccountRef]: ...
    def positions(self, account: AccountRef) -> Sequence[object]: ...
    def submit(self, intent: OrderIntent) -> object: ...
    def reconcile(self, account: AccountRef, intent_id: str) -> object: ...
    def move_stop(self, account: AccountRef, position_id: str, stop: Decimal) -> object: ...
    def close(self, account: AccountRef, position_id: str) -> object: ...

class MarketDataProvider(Protocol):
    def history(self, instrument_id: str, timeframe: str, count: int) -> Sequence[object]: ...
    def subscribe(self, instrument_ids: Sequence[str], sink: object) -> object: ...
    def status(self) -> object: ...

class RiskEngine(Protocol):
    def evaluate(self, intent: OrderIntent, snapshot: object) -> object: ...

class Strategy(Protocol):
    def evaluate(self, snapshot: object) -> Sequence[object]: ...
```

Les méthodes `submit/move_stop/close` doivent être indisponibles côté adaptateur réel en mode `ANALYSIS` et tant que l'activation sécurisée n'a pas réussi. Le contrat d'exécution réel doit inclure les champs broker nécessaires et des identifiants corrélables ; en l'absence d'idempotency-key native côté IG, seule la réconciliation empêche une resoumission aveugle.

### 17.1 Format minimal d'événement

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "correlation_id": "uuid",
  "causation_id": "uuid-or-null",
  "timestamp_utc": "2026-10-20T18:00:00Z",
  "event_type": "ORDER_RISK_REJECTED",
  "broker_id": "ig",
  "environment": "demo",
  "account_ref": "opaque-account-ref",
  "instrument_id": "GOLD_SPOT",
  "intent_id": "uuid",
  "strategy_id": "TREND_FOLLOW",
  "reasons": ["DAILY_RISK_LIMIT", "STALE_QUOTE"],
  "payload": {"estimated_loss_eur": "12.00", "limit_eur": "10.00"}
}
```

*L'exemple est synthétique ; il ne correspond à aucune transaction réelle.* L'event store doit référencer des comptes par identifiants internes/pseudonymes pour les exports.

### 17.2 Exemple de profil de configuration **sans secrets**

```yaml
schema_version: 1
runtime:
  platform: windows
  start_mode: analysis
  keep_gui_open: true
market_data:
  primary_provider: ig
  history_policy: cache_then_bounded_backfill
  chart_timeframe: 5m
  context_timeframes: [15m, 1h]
risk:
  per_trade_pct: 1.0
  daily_drawdown_pct: 3.0
  max_open_global: 1
  max_open_per_underlying: 1
  min_reward_risk_ratio: 2.0
trade_manager:
  break_even_trigger_r: 1.0
  secure_net_profit_buffer: 0.0
  trailing_enabled: false
scanner:
  weights:
    technical: 30
    sentiment: 15
    potential_rr: 20
    market_risk: 15
    execution_cost: 10
    data_quality: 10
  thresholds: {candidate: 75, watch: 60}
notifications:
  windows: true
  email: false
  telegram: false
```

Le GUI peut persister en JSON plutôt qu'en YAML pour compatibilité avec la configuration existante ; l'exigence porte sur la sémantique, le versionnement et la validation, pas sur l'extension du fichier.

## 18. Plan d’implémentation obligatoire pour Codex

Le développement est incrémental, avec test de sortie à chaque tranche et **pas d'accès live** avant jalon formel. Chaque phase dispose de tâches courtes, mesurables et revues.

| Phase | Contenu | Critère de sortie (Definition of Done) |
|---|---|---|
| **SR00 — Migration SR 4.1.0** | Diagnostic en lecture seule, preview officielle de la mise à niveau de l’ancien pack, validation humaine, upgrade SR seul puis contrôles | `SR_PACK_VERSION.json=4.1.0`, `sr_post_install_check` concluant, aucun fichier applicatif modifié ; **arrêt avant R00** |
| **R00 — Baseline** | Branche de travail depuis `512c16d`; inventaire diffs, dépendances, tests, capture GUI, état des comptes | `pytest`/Ruff/smoke documentés ; aucune écriture live ; fiche `CURRENT_STATE.md` à jour |
| **R01 — OHLC** | Corriger BUG-DATA-001/002/003 ; compaction après ; tests M1→M5, quota, non-blocage UI | Fixtures OHLC exactes, cache accessible quota épuisé, thread Qt non bloqué |
| **R02 — Contrats** | Introduire interfaces Broker/Data et capacités ; mapping sous-jacent/contrat, fake adapters | Tests contractuels multi-providers ; GUI existante conserve son comportement |
| **R03 — Comptes et risque** | Account Manager, snapshots, calculs equity, plafonds 1 %/3 %, limites global/marché | Tests multi-comptes, FX, réservations concurrentes, veto et kill switch |
| **R04 — Stockage & GUI** | Event Store, recorder, migrations, statistiques et nouveaux tabs/docks, settings complets | P&L recomptable, stats jour/semaine/mois, settings tous éditables, migration testée |
| **R05 — Analyse** | Indicateurs, stratégie registry, macro/sentiment, scanner, scoring, commentaire | Fixtures numériques, `WARMING_UP`, `NO_TRADE`, justifications auditées |
| **R06 — Paper & trade manager** | Ticket builder, PaperBroker, ordres conditionnels, sécurisation + trailing, alerts | Parcours paper intégral, confirmations fictives, aucun appel live, tests state machine |
| **R07 — API IG démo/supervisé** | Capability matrix Barrières/Options et CFD, order coordinator, réconciliation et confirmations | Tests démo et dossier preuves sanitizées ; supervised gate ; cas timeout/compte incorrect |
| **R08 — Automatisation optionnelle** | Activation AUTO, whitelists, surveillance, validation quantitative, exploitation | Kill switch/risk veto testés, reprise sûre, critères d'acceptation signés ; aucune activation implicite |

**Règle :** Codex ne saute pas une phase sans justifier explicitement la conformité des prérequis et les preuves de test. L'amélioration fonctionnelle peut être découpée davantage, mais les garde-fous ne sont jamais reportés après les appels live.

### 18.1 Tranche R00/R01 — seulement après SR00 vérifié

1. Vérifier `git status`, l'ancêtre de `main`, créer `codex/tradingig-prd-v1-restart` depuis `codex/stream-live-candle-robustness` (ne pas modifier `main` directement).
2. Installer dans un venv du dépôt les dépendances du `pyproject.toml`, identifier toute divergence Python 3.11/3.12 et verrouiller l'environnement choisi.
3. Exécuter `pytest -q`, `ruff check src tests` et smoke GUI ; noter résultats sans modifier la logique pour faire artificiellement passer les tests.
4. Ajouter test du **cache lisible malgré quota historique global épuisé**, puis corriger l'ordre de priorité dans `MainWindow`.
5. Ajouter test M1→M5 avec 5 bougies, ordres de mises à jour et valeurs extrêmes variées ; corriger le calcul canonique ; vérifier partiel/clôturé.
6. Séparer l'appel REST historique bloquant de la boucle Qt ; ajouter test avec faux provider lent et interaction GUI non bloquée.
7. Vérifier après patch : relecture cache, recalcul timeframes, changement de produit, Bid/Mid/Ask, reconnexion et sélection de compte.
8. Documenter `findings.md`, `progress.md`, `verification.md`, décisions/ADR, modifications et risques restants ; ne pas créer de fonction de trading réel.

### 18.2 Pratique Codex sous SR 4.1.0

- Après mise à niveau SR00, lire le **noyau court** de `AGENTS.md` et la route pertinente dans `docs/codex/SR_ROUTES.json` ; ne charger que les procédures déclenchées et les sources de code réellement nécessaires. Pour une modification non triviale, les contrôles SR sont **Scope**, **Verification** et, uniquement si une activation est demandée, **Activation**.
- Les skills spécialisés sont conditionnels : `aurora-diagnose` pour un bug réel, `aurora-architecture-check` pour une interface/schéma, `aurora-ui-visual-qa` pour une modification graphique, `aurora-lot-runner` pour une passe multilot validée. `aurora-to-prd` et `aurora-domain-skill-factory` restent facultatifs. Ne pas importer l’ancien catalogue de 10 skills comme règle 4.1.
- Conserver `docs/prd/PRD.md`, les fiches `F001..F011` et `docs/CURRENT_STATE.md` comme documents produit/projet à tenir alignés. Ce PDF/MD est la **baseline produit du 20 octobre 2026** ; les registres SR et la documentation modulaire sont la mémoire d’exécution.
- Présenter le périmètre et la preuve de validation proportionnelle à chaque tranche. Les tests de non-régression critiques restent obligatoires pour notre trading, **sans imposer le rituel TDD ni un test délibérément rouge**, retirés de SR 4.1.
- Ne jamais effectuer un appel IG d’ordre réel, un changement de compte actif ou une migration/déploiement sans autorisation spécifique ; aucune donnée secrète dans les artefacts.

### 18.3 SR Method 4.1.0 — contrat de développement obligatoire

**SR (Specification Runtime Method) est une méthode de pilotage de Codex et non une stratégie de trading.** Le dépôt contient déjà un pack Codex hérité (état constaté sur `codex/stream-live-candle-robustness`, mai 2026) avec `AGENTS.md`, scripts, RepoMap et mémoires de tâches. **Il ne doit pas être considéré comme SR 4.1.0 installé avant vérification.**

**Référence officielle :** [Aurora SR Method Codex Pack](https://github.com/syl2042/Aurora_SR_method_codex_pack) ; version publiée `4.1.0` le **24/09/2026**, d’après `core/SR_PACK_VERSION.json`, `CHANGELOG.md` et `INSTALLATION.fr.md`. Ne pas utiliser les consignes plus anciennes du site ou les historiques mémorisés pour substituer un autre catalogue de skills à la version 4.1.

#### 18.3.1 SR00 — migration indépendante du code applicatif

1. **Lecture seule :** sélectionner la branche de travail fondée sur `codex/stream-live-candle-robustness`, contrôler `git status`, versions/empreintes SR présentes et travail local non committé. Ne pas fusionner `main` ni modifier le code.
2. **Source explicite :** pointer `SR_PACK_SOURCE` vers le dépôt officiel ; vérifier URL, commit source, état Git, `version=4.1.0` et `release_status=released`. Enregistrer ce commit dans le rapport SR00.
3. **Prévisualisation uniquement :** exécuter le plan officiel sans écriture : `python scripts/install_codex_pack.py --source <SR_PACK_SOURCE> --target <TradingIG> --json` (avec l’interpréteur du venv et les chemins Windows adaptés). Classer les fichiers absents, gérés, personnalisés, obsolètes ou conflictuels.
4. **Validation humaine :** soumettre la liste exacte des fichiers qui seront modifiés, préservés et éventuellement supprimés. **Ne pas passer à `--upgrade` sans approbation de cette liste**, même si le présent PRD est validé.
5. **Upgrade conservateur :** seulement après validation, utiliser `--upgrade` pour une installation ancienne, partielle ou modifiée. Ne pas réinstaller en mode neuf `--write` quand des marqueurs SR existent. Préserver toutes les mémoires, lots, passes, handoffs, compétences locales, instructions personnalisées, travaux non committés et artefacts métier.
6. **Contrôle :** exécuter `scripts/codex/sr_post_install_check.py --root . --json`, `git diff --check`, `git status --short` et les vérificateurs SR réellement présents. Un code de sortie installateur `0` seul **ne prouve pas** la conformité. Si le rapport est rouge, classer SR00 comme incomplet.
7. **Fin de SR00 :** livrer versions, source commit, conflits, état des skills, vérifications, chemins modifiés et dérogations ; **arrêter avant de coder R00/R01**. Si nécessaire, proposer le réalignement mémoire en suivant `prompts/fr/07_realign_sr_state_after_upgrade.md`, avec validation séparée. Ne fermer aucun lot applicatif par effet de bord.

**Interdictions durant SR00 :** toucher `src/`, les tests métier, `pyproject.toml`, les secrets, les migrations SQLite, les positions/ordres, les paramètres de trading, ou activer des outils MCP/Nexus. La migration SR n'est ni une mise à jour applicative ni un déploiement.

#### 18.3.2 Fichiers SR et hiérarchie d'autorité

| Artefact | Usage attendu après upgrade |
|---|---|
| `AGENTS.md` | Noyau court de règles permanentes, routes et garde-fous TradingIG ; préserver les règles locales |
| `docs/codex/SR_BOOTSTRAP.md`, `SR_ROUTES.json` | Procédures à lire selon l'action, pas chargement systématique du pack |
| `docs/codex/PROJECT_PROFILE.yaml`, `SKILL_DIGEST.md` | Configuration `knowledge.mode`, sélection exacte de skills ; pas d'ancien catalogue obligatoire |
| `docs/codex/SR_LOTS.yaml`, `SR_PASSES.yaml`, `SR_INBOX.yaml` | Backlog atomique, passes bornées, demandes/décisions à trier ; zéro lot inventé à l'installation |
| `docs/codex/tasks/.../task_state.yaml` | Mémoire compacte d'une tâche non triviale ; anciens `task_plan`, `findings`, `verification` restent lisibles |
| `docs/CURRENT_STATE.md`, `CODEBASE_MAP.md` | Reprise fondée sur l'état réel ; code et tests prévalent sur la carte et les résumés |
| `docs/codex/MCP_POLICY.yaml` | Politique de capacités MCP ; mode `core` par défaut et **aucun MCP** en ce mode SR |
| `docs/codex/project-skills/` | Skills de domaine TradingIG locaux après validation humaine, pas de publication globale automatique |

**Autorité :** spécifications approuvées (`REQ-*` et décisions), code réel et tests pour les faits d'implémentation, registres SR pour l'état du travail. Ne jamais convertir massivement les anciens contrats SR, ni effacer leurs preuves pour les aligner visuellement.

#### 18.3.3 Exécution des lots et trois frontières

- **Scope Gate (avant mutation non triviale) :** expliciter résultat observable, chemins autorisés, fichiers sensibles, hypothèses, contrats/consommateurs affectés, risque, tests ciblés et limites de la tranche. Demander autorisation si changement de périmètre, schéma critique ou couplage externe.
- **Verification Gate (fin du travail) :** valider à coût proportionné aux risques : tests unitaires/contrats/replay ciblés, `ruff`, imports, contrôle de logs/secrets, vérification des conséquences sur les consommateurs. Les tests d'ordres, de positions, de risque, d'OHLC et de réconciliation sont **indispensables selon leur périmètre** ; SR 4.1 n'impose ni TDD cérémoniel ni faux échec initial.
- **Activation Gate (seulement pour build, redémarrage, déploiement ou activation demandés) :** expliciter l'artefact activé, preuves du runtime et procédure de retour arrière. Dans TradingIG, activer la voie réelle `SUPERVISED`/`AUTO` est une autorisation sensible **distincte de l'autorisation de développer du code**. Aucun accès live créé/activé pendant SR00–R06.

Pour les changements étendus, grouper des lots cohérents dans une *SR Pass* approuvée, vérifier dépendances, ne pas multiplier les micro-validations, arrêter sur vraie décision bloquante. Une tâche simple peut se terminer sans nouvel artefact SR. Les bilans doivent distinguer **fait**, **vérifié**, **non vérifié** et **acceptation humaine restante**.

#### 18.3.4 Domain skills et méthode des agents IA runtime

Proposer, mais **ne pas créer sans validation**, des compétences locales TradingIG : `tradingig-ig-api-capabilities`, `tradingig-market-data-integrity`, `tradingig-risk-and-order-safety`, `tradingig-pyqt-windows-qa`. Elles décrivent les pièges du domaine et les sources de vérité, non de nouveaux privilèges d'exécution.

Les futurs agents IA de sentiment ou de trading doivent respecter le **SR Agent Method** : action produit bornée, entrée et sortie typées, provenance/fraîcheur, distinction outil de lecture / action d'ordre, contrat d'agent et validation humaine pour toute action sensible non déléguée. L'autorisation AUTO, lorsqu'elle sera explicitement accordée, reste soumise au moteur de risque déterministe, aux limites de positions et à la réconciliation du broker.

La configuration initiale de connaissance sera `knowledge.mode: core`, **sans appels MCP** dans ce mode de fonctionnement Codex. Toute activation future `nexus_kg` requiert une décision séparée et une `MCP_POLICY.yaml` explicite (outils autorisés, lecture/écriture, confidentialité, budgets, retries et approbations). Cela ne proscrit pas les appels réseau métier IG de l'application : la règle MCP concerne les outils de connaissance de Codex.

#### 18.3.5 Vérification UI adaptée à Windows/PyQt5

Les vérifications visuelles de SR 4.1 sont déclenchées pour une modification graphique significative. **TradingIG étant une GUI native PyQt5, il ne faut pas supposer qu'une URL Playwright existe.** Codex proposera la voie réellement disponible : tests Qt ciblés, captures d'écran Windows hors données sensibles, scénarios utilisateur M1/M5 et comptes, et rapport d'inspection visuelle. Le runner web SR ne sera utilisé que pour un éventuel composant web réellement présent.

**Critères d'acceptation méthode SR :** `AC-SR-001` source publiée et commit enregistré ; `AC-SR-002` migration sans mutation métier ni perte des personnalisations ; `AC-SR-003` post-install check satisfaisant ; `AC-SR-004` reprise à partir du véritable état de la branche avancée ; `AC-SR-005` aucun ordre réel ou déploiement implicite ; `AC-SR-006` traçabilité exigences → lots → preuves → validation.

## 19. Grille de tests d'acceptation de bout en bout

| ID | Scénario | Résultat attendu |
|---|---|---|
| AC-001 | `main` ancien et branche avancée comparées | L'application repart de `512c16d` sur une branche de travail, aucun code fonctionnel perdu |
| AC-002 | Quota historique IG épuisé, cache présent | Le cache local est chargé sans tentative REST répétée |
| AC-003 | Cinq sous-bougies M1 forment un M5 | O/H/L/C et statut clôturé corrects, même en cas d'updates multiples |
| AC-004 | Requête historique lente de 20 s simulées | La GUI continue de recevoir clics et rafraîchissements non bloquants |
| AC-005 | CFD et Barrières d'un même sous-jacent | Les deux comptes sont affichés, exposition regroupée, plafond marché partagé |
| AC-006 | Changement de compte refusé | Aucun ordre/signal d'exécution dirigé vers le mauvais compte |
| AC-007 | P&L journalier atteint -3 % | Plus de nouvelles ouvertures ; gestion des positions toujours active |
| AC-008 | Position globale existante, plafond 1 | Deuxième ordre pending/exécuté refusé, y compris en concurrence |
| AC-009 | Analyse technique 80/100, sentiment IA opposé | Score et divergence expliqués ; le Risk Engine peut bloquer séparément |
| AC-010 | Indicateur sans warmup suffisant | `WARMING_UP`, aucune décision exécutable |
| AC-011 | Profit atteint +1R | Stop net proposé avec frais, sans garantie d'exécution ; statut protégé après confirmation broker |
| AC-012 | Broker refuse l'update stop | Position ne passe pas `PROTECTED`, alerte et audit |
| AC-013 | Réponse ordre timeout | `UNKNOWN`, réconciliation avant toute nouvelle commande ; zéro renvoi aveugle |
| AC-014 | Mode `ANALYSIS` et clic « Trader » | Aucun appel HTTP d'ordre ; éventuelle proposition paper séparée |
| AC-015 | Fermeture GUI avec pending logiciel | Avertissement et indication de perte de protection si arrêté |
| AC-016 | Notification SMTP/Telegram échec | Événement d'alerte reste visible localement ; aucune influence sur Risk Engine |
| AC-017 | Historique journal importé | Statistiques jour/semaine/mois concordantes nettes de frais, pas de doublons |
| AC-018 | Stratégie testée sur données futures | Test temporel détecte ou interdit une fuite de données dans le replay |
| AC-019 | LLM produit un ordre non conforme | Rejet déterministe indépendant du commentaire IA |
| AC-020 | API KO Barrières non supportée | Capacité `UNSUPPORTED`, route d'ordre désactivée, explication utilisateur |
| AC-SR-001..006 | SR00 version publiée, préservation des personnalisations et post-check | Source SR 4.1.0 vérifiée ; aucune modification du code métier ; validation humaine séparée |

## 20. Risques ouverts, limites externes et jalons bloquants

1. **IG Barrières/Options :** disponibilité réelle de la découverte KO, ouverture, modification stop et clôture selon pays, environnement et compte ; exiger un spike documenté de requêtes/réponses **expurgées** avant R07.
2. **Sessions IG multi-comptes :** déterminer contraintes REST et streaming, changement de contexte atomique, concurrence et comportements de tokens ; tests en démo.
3. **Historique / quotas :** l'allocation et les limites API peuvent évoluer ; ne pas coder une constante immuable. Vérifier sur le compte réel sans multiplier les requêtes.
4. **Fournisseur de news/sentiment :** coûts, licences, horodatages, qualité, politique de conservation et capacité de replay ; choix d'adaptateur et fournisseur configurable.
5. **Précision du risque d'une barrière :** règles de KO, prime, taille, slippage, frais et financement validées sur paramètres broker ; bloquer si prix/contrat insuffisamment décrits.
6. **Qualité des backtests intraday :** des OHLC M1 sans vraie granularité d'exécution peuvent masquer le chemin intra-bougie ; marquer le résultat comme approximation.
7. **Exposition dépendance réseau :** une gestion logicielle de stop/ordre pending ne remplace pas une protection effectivement acceptée par le broker.
8. **Utilisation IA :** sentiment directionnel ≠ probabilité de hausse vérifiée ; score de confiance déclaré ≠ calibration ; l'automatisation exige une comparaison empirique.

**Les points 1, 2 et 5 sont bloquants pour exécuter des Barrières/Options IG en mode réel, pas pour coder les composants abstraits, le Risk Engine ou le mode paper.**

## 21. Correspondance avec la documentation existante

| Document du dépôt | Action Codex |
|---|---|
| `docs/prd/PRD.md`, `01_product/*` | Réviser vision, mode auto à terme, décisions, KPIs, scope et risques |
| `10_architecture/overview.md`, `module_boundaries.md`, `main_flows.md` | Ajouter interfaces broker/data, runtime GUI permanent, multi-comptes et exécution sûre |
| `10_architecture/data_schema.md` | Réviser snapshots, instruments, fills, événements, signaux non exécutés, IA, FX et config |
| `F001`, `F002`, `API001`, `API002` | Étendre les comptes, capabilities, quotas et processus de validation IG |
| `F003` | Qualité OHLC, cache, threading, timeframes, warmup |
| `F004` | Stratégies, scoring pondéré et **colonne commentaire** |
| `F005`, `F011`, `API003` | Sentiment, confiance, fournisseurs, provenance et macro ribbon |
| `F006` | Risk Engine 1 %/3 %, exposures, KO, ticket net et limites de positions |
| `F007`, `F008` | Pending, réconciliation, mode auto, break-even net, sécurisation, trailing |
| `F009`, `F010` | Recorder des non-trades, P&L agrégé, imports et replay réaliste |
| `02_tasks/*` et `05_coding_agent/*` | Ajouter SR00 puis phases R00–R08 ; remplacer les anciennes consignes procédurales par les routes SR 4.1 sans effacer les traces historiques |
| `AGENTS.md`, `docs/codex/SR_*`, `PROJECT_PROFILE.yaml` | Réconcilier via l’installateur **officiel**, avec rapport preview/upgrade et validation de préservation ; ne pas éditer manuellement le noyau géré avant le diagnostic |
| `90_quality/*`, `AGENTS.md`, `CURRENT_STATE.md` | Mettre à jour gates sécurité, définition de Done et suivi d'exécution |

## 22. Definition of Done générale

Un lot est « terminé » uniquement si :

1. Le besoin, les risques, les interfaces et les paramètres GUI associés sont documentés et référencés par `REQ-*`.
2. Les tests unitaires et de contrat couvrent valeurs normales, limites, indisponibilité, déconnexion et erreurs ; ils ont été exécutés ou impossibilité documentée.
3. `ruff` et les vérifications d'import/importabilité passent ; smoke GUI Windows effectué pour tout changement d'interface.
4. Les calculs sont reproductibles, déterministes et horodatés ; les comportements non supportés sont visibles.
5. Les secrets sont absents des sources et logs ; la sécurité d'exécution n'est pas réduite.
6. Le diff et l’impact ont été contrôlés ; une preuve de vérification proportionnée est consignée dans `task_state.yaml` ou la mémoire de lot existante, sans créer artificiellement tous les anciens fichiers à chaque tâche.
7. Les anciens workflows qui fonctionnaient restent vérifiés par tests de non-régression ; pas de « refactor global » opportuniste.
8. Le résultat est démontrable via test, capture GUI non sensible ou replay documenté, avec critères d'acceptation reliés aux exigences.

## 23. Premier prompt de démarrage Codex

> Tu travailles sur `stephanerey/TradingIG`, référence `codex/stream-live-candle-robustness` (`512c16d...`). Le PRD **V1.1** impose la **SR Method 4.1.0**. Première mission **SR00 uniquement** : examine l'installation SR héritée, sélectionne la source officielle `syl2042/Aurora_SR_method_codex_pack`, confirme `version=4.1.0` et `release_status=released`, vérifie l'état Git et génère un plan d'upgrade en lecture seule avec `--json`. **Présente les fichiers à modifier et préserver et attends ma validation explicite avant `--upgrade`.** Après autorisation séparée, applique exclusivement la migration SR, vérifie le résultat avec `sr_post_install_check`, puis arrête sans commencer le développement R00/R01 ni toucher aux ordres, au code métier ou aux secrets. Le prompt R00/R01 séparé ne sera utilisé qu'après SR00 satisfaisant.

---

**Sources techniques du projet et de la méthode :**

- Dépôt : <https://github.com/stephanerey/TradingIG>
- Branche auditée : <https://github.com/stephanerey/TradingIG/tree/codex/stream-live-candle-robustness>
- Findings des bougies : <https://github.com/stephanerey/TradingIG/blob/codex/stream-live-candle-robustness/docs/codex/tasks/2026-05-12_stream-live-candle-robustness/findings.md>
- PRD existant : <https://github.com/stephanerey/TradingIG/blob/codex/stream-live-candle-robustness/docs/prd/PRD.md>
- Consignes agent héritées : <https://github.com/stephanerey/TradingIG/blob/codex/stream-live-candle-robustness/AGENTS.md>
- SR Method 4.1.0 : <https://github.com/syl2042/Aurora_SR_method_codex_pack>
- Changelog officiel : <https://github.com/syl2042/Aurora_SR_method_codex_pack/blob/main/CHANGELOG.md>
- Guide français 4.1 : <https://github.com/syl2042/Aurora_SR_method_codex_pack/blob/main/INSTALLATION.fr.md>

**Fin du PRD V1.1 — méthode SR 4.1.0.**
