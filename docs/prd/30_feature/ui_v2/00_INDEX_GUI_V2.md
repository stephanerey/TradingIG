# TradingIG — PRD GUI V2 | Référentiel modulaire

**Version de spécification :** GUI-V2.0 / 2026-11-09  
**Statut :** prêt pour découpage en lots SR 4.1 ; non implémenté / non accepté à ce stade  
**Cible :** Windows, Python 3.12, PyQt5, PyQtGraph  
**Dépôt examiné :** `stephanerey/TradingIG`, branche `chore/sr41-upgrade`, commit `1844916acec43d5ef0dc692d5235214dc46c5a9b` (09/11/2026).  
**Documents maîtres du projet :** `docs/prd/PRD.md`, `F012_windows_workspace_and_settings.md`, `F013_alerts_diagnostics_and_resilience.md` et le PRD V1.2. Ce dossier est un **addendum compatible** à fusionner sous contrôle, pas un remplacement de ces documents.

## Objectif

Transformer l'interface provisoire en **poste de travail de trading** lisible, moderne, réactif et bilingue **français/anglais** sans réécrire les moteurs IG, marché, scanner, IA ou Paper existants. Le modèle visuel est celui des maquettes générées et approuvées par l'utilisateur : thème sombre navy, sidebar, bandeau permanent, onglets internes, graphiques et tables alignés, codes de couleur sémantiques.

## Décisions explicitement validées

- Style sombre des maquettes, avec possibilité future de thème clair.
- Menu latéral fixe et comptes/états visibles en haut sur **toutes** les pages.
- Onglets par section et panneaux secondaires configurables, sans tout afficher simultanément.
- Dashboard de performance, positions et calendrier; scanner multi-marchés; watchlist/analyse; suivi des positions; historique/analyse des performances; macro/IA; diagnostics; paramètres.
- Variation des marchés et PnL en vert/rouge; seuils de surbrillance forts optionnels.
- Scénarios haussiers et baissiers. Exposition économique d'un dérivé et sens d'ordre IG sont distincts.
- IA capable de **proposer** des améliorations des paramètres à partir des résultats historiques, mais **sans auto-modification ni auto-exécution non autorisée**.
- FR et EN requis dans cette refonte (basculables depuis les paramètres).

## Décisions d'implémentation proposées dans cet addendum

Propositions techniques, à affiner uniquement si le code démontre une incompatibilité : `QStackedWidget` pour les pages principales, `QTabWidget` pour les sections, `QDockWidget` pour un futur mode Expert (non obligatoire sur l'accueil), `QTableView` + `QAbstractTableModel` pour les tables à forte actualisation, `QTranslator` pour i18n, thème Qt via palette/QSS, façades applicatives et view models indépendants du courtier.

## Arborescence documentaire

| Document | Objet | Références |
|---|---|---|
| [01 — Périmètre et navigation](01_VISION_NAVIGATION.md) | Shell, flux, niveaux, comportement | `GUI2-NAV-*` |
| [02 — Design System](02_DESIGN_SYSTEM.md) | Apparence, couleur, composants, responsive | `GUI2-DS-*` |
| [03 — Dashboard](03_DASHBOARD.md) | PnL, solde, stats, IA, news et positions | `GUI2-DASH-*` |
| [04 — Scanner / catalogue](04_SCANNER_CATALOGUE.md) | Scores, filtrage, listes et fraîcheur | `GUI2-SCAN-*` |
| [05 — Watchlist et analyse](05_WATCHLIST_ANALYSE.md) | Charts, stratégies, scénarios long/short | `GUI2-WATCH-*` |
| [06 — Positions / ordres](06_POSITIONS_ORDRES.md) | Paper, broker, stops/KO, actions sécurisées | `GUI2-ORD-*` |
| [07 — Historique et optimisation](07_HISTORIQUE_IA_APPRENTISSAGE.md) | Statistiques, diagnostics de stratégie, propositions IA | `GUI2-ANA-*` |
| [08 — Macro et IA](08_MACRO_IA.md) | Calendrier, preuves, contextes et coût IA | `GUI2-MAC-*` |
| [09 — Diagnostic / paramètres](09_DIAGNOSTICS_PARAMETRES.md) | Santé, alertes, contrôle du risque et configuration | `GUI2-OPS-*` |
| [10 — Internationalisation](10_I18N_FR_EN.md) | Traductions Qt et localisation | `GUI2-I18N-*` |
| [11 — Contrats et disponibilité](11_CONTRATS_ETATS_DONNEES.md) | DTO, snapshots, états, unités et calculs | `GUI2-DATA-*` |
| [Architecture GUI V2](../../10_architecture/gui_v2_refactor.md) | Comment transformer le code sans le casser | `GUI2-ARCH-*` |
| [Lotissement R09](../../02_tasks/phases/R09_gui_v2.md) | Séquence Codex / SR 4.1 | `GUI2-LOT-*` |
| [Consignes Codex](../../05_coding_agent/gui_v2_codex_guide.md) | Scope, Verification, Activation et interfaces | Exécution |
| [Plan de QA GUI V2](../../90_quality/gui_v2_qa.md) | Matrice d'acceptation, captures, tests | `AC-GUI2-*` |

## Références visuelles

Images **illustratives**, obtenues par génération graphique. Les chiffres, ordres, cotations et statuts visibles sont des **données fictives**. Les maquettes ne prouvent ni l'existence d'une fonctionnalité, ni sa disponibilité via l'API IG. Les spécifications écrites et les contrats applicatifs priment sur les pixels.

- [Dashboard](../../95_sources/images/ui_v2/01_dashboard.png)
- [Scanner](../../95_sources/images/ui_v2/02_scanner.png)
- [Watchlist / Analyse](../../95_sources/images/ui_v2/03_watchlist_analyse.png)
- [Positions / Ordres](../../95_sources/images/ui_v2/04_positions_ordres.png)
- [Montage six écrans](../../95_sources/images/ui_v2/05_montage_ecrans.png)
- [Vues complémentaires](../../95_sources/images/ui_v2/06_vues_complementaires.png)

## Périmètre produit et sécurité

Ce lot concerne d'abord **l'interface et les projections**. Il ne doit ni ouvrir une position réelle, ni activer AUTO, ni élargir les capacités d'ordre IG. Connexion IG LIVE **en lecture seule** compatible avec exécution `PAPER` locale. Un test CFD DEMO borné antérieur ne vaut pas autorisation de trading général CFD, Barrières ou Options. Les statistiques broker LIVE incomplètes ne doivent jamais être inventées ni assimilées aux métriques Paper.

## Définitions transversales

- `underlying_id` : identité du marché de référence ; `product_epic` : instrument IG négocié, jamais déduit du nom.
- `data_mode` : DEMO/LIVE du fournisseur de cotation ; `execution_mode` : ANALYSIS, PAPER, SUPERVISED_DEMO, etc. (capacités effectivement autorisées seulement).
- `analysis_status` : `READY`, `WARMING_UP`, `STALE`, `DATA_GAP`, `UNAVAILABLE`, `NOT_APPLICABLE` ; `UNKNOWN` reste absent de tout score numérique.
- `signal_direction` : `BULLISH`, `BEARISH`, `NEUTRAL` (perspective marché), séparé de `order_side` `BUY`/`SELL` et du type de produit.
- `scope` : compte/produit/marché/période ; chaque KPI et toute analyse IA portent leur scope, leurs sources et leur date.

## Critère de réussite global

Un utilisateur peut ouvrir TradingIG et comprendre sans ambiguïté **quel compte est sélectionné**, quel environnement fournit les cotations, si l'exécution est simulée, quels marchés ont des données fraîches, ce qui est connu/inconnu, quelle est la performance attestée et quelles actions nécessitent validation. La nouvelle GUI ne change pas les résultats déterministes des moteurs existants.
