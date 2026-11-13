# CODEBASE_MAP.md — carte humaine courte

## Vue d'ensemble
- Type : application desktop Windows Python 3.12, PyQt5 et PyQtGraph.
- Package : `src/trading_ig_assistant`.
- Entrée : `trading_ig_assistant.main:main`; sans argument, GUI legacy.
- GUI V2 : opt-in via `trading-ig-assistant gui --ui v2` pendant la migration.
- Tests : pytest hors ligne sous `tests/`; lint ciblé `ruff check src tests`.

## Répertoires importants

```text
src/trading_ig_assistant/domain/       # contrats métier purs
src/trading_ig_assistant/services/     # scanner, risque, Paper, analytics, replay
src/trading_ig_assistant/adapters/     # IG, streaming, OpenAI, sources externes
src/trading_ig_assistant/persistence/  # SQLite et checkpoints Paper explicites
src/trading_ig_assistant/app/          # config, runtime de projections et façade UI
src/trading_ig_assistant/ui/           # GUI legacy et fondations V2
tests/                                 # tests unitaires et intégration hors ligne
docs/prd/                              # PRD produit et addendum GUI V2
```

## Modules critiques
- `ui/main_window.py` : coordonne encore les workers Qt, le streaming et Paper; la session REST read-only est désormais déléguée au runtime, qui reçoit aussi les projections legacy.
- `app/runtime/trading_runtime.py` : propriétaire unique de la session IG REST read-only et des snapshots GUI immuables; abonnements et rejet des anciennes générations, aucune commande broker.
- `app/runtime/ig_session_runtime.py` : cycle login/compte/logout pour un seul adaptateur `read_only=True`, avec confirmation stricte des changements de compte.
- `app/qt_connection_controller.py` : intentions V2 explicites connexion DEMO ou LIVE read-only,
  déconnexion et changement de compte, exécutées par workers Qt; profils/coffres isolés par
  environnement et aucune commande d’ordre.
- `app/qt_catalogue_controller.py` : charge l'inventaire local complet sans réseau, permet un complément manuel `search_markets` et résout au double-clic les métadonnées d'un seul produit configuré via `get_market_details`, sans crawl de détails.
- `app/qt_market_stream_controller.py` : une connexion Lightstreamer et un budget total borné à 40 items : 1 compte, 5 graphiques de référence et jusqu'à 34 cotations catalogue; les produits suivis explicitement et ceux des positions de simulation ouvertes sont prioritaires. Un produit suivi conserve son flux PRICE exact même si son EPIC est aussi une référence CHART, afin qu'un refus CHART ne masque pas une cotation produit autorisée.
- `app/qt_scanner_session_controller.py` : collecte OHLC 1 minute `session-only` pour les cinq références, suivi du warm-up et réévaluation automatique du scanner à chaque nouvelle bougie; aucun historique REST ni ordre.
- `app/qt_paper_session_controller.py` : propriétaire V2 de la session Paper locale, ouverture confirmée et réévaluée, sauvegarde/restauration explicites, publication dashboard/journal/santé SQLite; aucun chemin d'ordre IG.
- `app/projections/account*.py`, `app/projections/dashboard*.py` : snapshot REST compte IG typé fusionné aux métriques ACCOUNT temps réel attestées et au dashboard PAPER; positions et PnL réalisé restent locaux.
- `app/projections/scanner*.py` : cinq marchés configurés toujours visibles, prix/fraîcheur, progression OHLC, scores déterministes et raisons d'indisponibilité sans donnée inventée.
- `app/projections/paper_history*.py` : journal Paper append-only expurgé pour l'UI, sans payload interne ni mélange Paper/broker.
- `app/projections/paper_ticket.py` : contrôle préalable strict d'un produit catalogue exact avant préparation Paper; binding configuré, cotation live fraîche, métadonnées produit et devise attestée sont obligatoires, sans inférence par libellé.
- `app/projections/macro*.py`, `app/qt_macro_context_controller.py` : collecte RSS Fed/BCE uniquement sur action explicite; appel OpenAI consultatif distinct, borné, lancé seulement après aperçu et consentement à usage unique, sans exécution automatique.
- `app/projections/optimization*.py` : diagnostic local gouverné de l'aptitude du dataset; état `INSUFFICIENT_EVIDENCE`, blocages auditables et aucune proposition tant que versions/replay hors échantillon manquent.
- `app/ui_facade.py` : frontière de lecture consommée par le shell V2.
- `ui/shell/main_window_v2.py` : shell V2 opt-in, sans connecteur direct; bandeau compte branché
  au contrôleur applicatif DEMO/LIVE read-only, avec exécution de simulation uniquement. Il active
  une liste de produits suivis distincte par environnement/compte et transforme leurs cotations
  PRICE exactes en bougies M1 de session sans les injecter dans le Scanner de références.
- `ui/shell/account_header.py` : connexion à gauche par sélecteur DEMO/LIVE et action média
  PLAY/STOP, identité cohérente avec nom/type broker et identifiant masqué, menu de comptes stable
  pendant les ticks, puis cartes Equity/Solde/Disponible/PnL à droite avec état financier sémantique.
- `ui/pages/dashboard_page.py`, `ui/models/position_table_model.py` : dashboard V2 read-only, KPIs Paper attestés, histogramme PnL période/devise et table Qt alimentés uniquement par projections; equity/% restent N/A sans snapshots historiques.
- `ui/pages/scanner_page.py`, `ui/models/product_table_model.py`, `ui/models/scanner_market_table_model.py` : catalogue complet en premier onglet, filtre local instantané, ajout explicite d'un produit exact aux valeurs suivies, fraîcheur et quatre vues scanner par marché de référence.
- `ui/pages/watchlist_page.py`, `ui/pages/paper_ticket_preparation.py` : liste utilisateur initialement vide pour tout nouveau couple environnement/compte, ajout depuis le catalogue courant, retrait manuel et persistance des EPIC exacts sans transposition DEMO/LIVE. Le graphique est session-only sur le produit suivi; les signaux techniques ne sont projetés que lorsqu'un binding explicite les relie au Scanner et sont filtrés sur ce produit exact. La fiche de preuves et le brouillon de simulation restent évalués par le TicketBuilder/RiskEngine existant; après confirmation explicite par défaut à Non, seule une position locale peut être ouverte et aucune commande broker n'est exposée.
- `ui/pages/positions_page.py`, `ui/pages/history_page.py` : positions PAPER, sauvegarde/restauration locale explicites, journal filtrable, PnL et statistiques réalisées par devise; données broker absentes séparées explicitement.
- `ui/pages/macro_page.py`, `ui/pages/diagnostics_page.py`, `ui/pages/settings_page.py` : actualités officielles à rafraîchissement manuel, analyse IA manuelle avec modèle/limite/aperçu/consentement, santé observée et réglages UI sans activation LIVE/AUTO.
- `ui/theme/tradingig_dark.qss` : palette centralisée des vues et contrôles natifs Qt, y compris inputs, combos/popups, états désactivés et scrollbars.
- `ui/chart_view.py` : graphique PyQtGraph réutilisé, avec surface, axes, chips et infobulles alignés sur le thème sombre; l'axe compact supprime les trous temporels sans fabriquer de bougies et utilise des corps larges avec libellés dédupliqués. Un vrai écart clôture→ouverture reste intact, est relié en pointillé ambré et son delta est explicité au survol. Environnement de données, EPIC source, base Bid/Mid/Ask, timeframe et dernier UTM sont affichés près du graphe pour empêcher une comparaison DEMO/LIVE ambiguë. Les lignes synthétiques Stop/Limit/KO ont été supprimées : seules la zone d'entrée, l'invalidation et la cible d'un signal projeté peuvent être superposées et désactivées individuellement.
- `services/paper_session.py` : frontière locale Paper indépendante d'IG; `services/analytics_service.py` agrège PnL et statistiques uniquement sur clôtures attestées.
- `services/scanner_runtime_batch_service.py` : scanner multi-marchés à bindings exacts.
- `adapters/ig_rest.py` : mutations broker bloquées par `LiveTradingDisabledError`.

## Commandes critiques
- `python -m pytest -q`
- `python -m ruff check --no-cache src tests`
- `trading-ig-assistant gui` : legacy par défaut.
- `trading-ig-assistant gui --ui v2` : shell V2 opt-in, connexion DEMO/LIVE read-only,
  catalogue/scanner/watchlist et vues PAPER.

## Zones risquées
- Qt : workers, timers et modèles doivent rejoindre le thread GUI par signaux.
- Compte/streaming : conserver génération, confirmation du compte et abonnement unique.
- Données : OHLC de runtime `session-only`; aucun backfill/cache de démarrage implicite.
- Paper : sauvegarde/restauration uniquement sur action; aucun chemin vers IG.
- Secrets : keyring/environnement seulement; jamais dans config, logs ou projections.
