<div class="cover">
  <div class="cover-top">TRADING IG ASSISTANT &nbsp; / &nbsp; DOCUMENT DE RÉFÉRENCE</div>
  <div class="cover-title">PRD GUI V2</div>
  <div class="cover-subtitle">Interface Windows · Design System sombre · FR / EN · Architecture Codex</div>
  <div class="cover-version">Édition 9 novembre 2026 &nbsp; · &nbsp; SR Method 4.1</div>
  <p>Référence visuelle : voir docs/prd/95_sources/images/ui_v2/REFERENCE_IMAGES.md (captures PNG non incluses dans la publication GitHub).</p>
  <div class="cover-footer">SOURCES MODULAIRES &nbsp; · &nbsp; R09 GUI &nbsp; · &nbsp; 98 EXIGENCES &nbsp; · &nbsp; PRÉSERVATION DU TRADING PAPER</div>
</div>

# Synthèse d'exécution

**Objectif** : transformer la GUI provisoire de TradingIG en poste de travail de trading moderne et bilingue, sans perturber les services IG, OHLC, scanner, IA ou Paper. La nouvelle interface est une **refonte de présentation et d'orchestration** ; elle ne constitue pas une autorisation de trading réel ou automatique.

**Décision de design validée** : thème dark navy, sidebar gauche, barre permanente de compte/risque/connexion, onglets internes, tableaux lisibles, graphiques synchronisés, badges vert/rouge et états inconnus explicites. Références visuelles incluses ci-dessous.

**Architecture** : faire évoluer `ui/main_window.py` (3 558 lignes au commit référencé) vers un shell composant des pages, alimenté par un runtime/facade unique et des projections typées. Maintenir une voie de repli vers l'ancienne GUI pendant migration.

**FR/EN** : Qt `QTranslator`/`QLocale` dès les fondations; bascule paramétrable et non destructive.

**Cible de première livraison** : shell et navigation; Dashboard à données attestées; Scanner/watchlist; positions Paper; Macro/IA/diagnostic; tests natifs Windows; recommandations d'optimisation IA **avec validation humaine**.

**Référence de code** : branche `chore/sr41-upgrade`, commit `1844916`, 9 novembre 2026; toutes les décisions et résultats doivent être reconfirmés par Codex sur la branche réellement utilisée.

**Avertissement** : toutes les captures d'interface incluses sont des maquettes artistiques avec chiffres, signaux et actions fictifs. Les règles métier restent celles du code et des spécifications écrites validées.

## Carte des documents

| Volet | Source dans le pack |
|---|---|
| Navigation & thème | `01_VISION_NAVIGATION.md`, `02_DESIGN_SYSTEM.md` |
| Dashboard & performances | `03_DASHBOARD.md`, `07_HISTORIQUE_IA_APPRENTISSAGE.md` |
| Scanner & watchlist | `04_SCANNER_CATALOGUE.md`, `05_WATCHLIST_ANALYSE.md` |
| Paper & positions | `06_POSITIONS_ORDRES.md` |
| Macro/IA & diagnostics | `08_MACRO_IA.md`, `09_DIAGNOSTICS_PARAMETRES.md` |
| Traduction et données | `10_I18N_FR_EN.md`, `11_CONTRATS_ETATS_DONNEES.md` |
| Codex/architecture et QA | `gui_v2_refactor.md`, `R09_gui_v2.md`, `gui_v2_codex_guide.md`, `gui_v2_qa.md` |

---



<!-- SOURCE: docs/prd/30_feature/ui_v2/00_INDEX_GUI_V2.md -->

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
| [01 — Périmètre et navigation](prd/30_feature/ui_v2/01_VISION_NAVIGATION.md) | Shell, flux, niveaux, comportement | `GUI2-NAV-*` |
| [02 — Design System](prd/30_feature/ui_v2/02_DESIGN_SYSTEM.md) | Apparence, couleur, composants, responsive | `GUI2-DS-*` |
| [03 — Dashboard](prd/30_feature/ui_v2/03_DASHBOARD.md) | PnL, solde, stats, IA, news et positions | `GUI2-DASH-*` |
| [04 — Scanner / catalogue](prd/30_feature/ui_v2/04_SCANNER_CATALOGUE.md) | Scores, filtrage, listes et fraîcheur | `GUI2-SCAN-*` |
| [05 — Watchlist et analyse](prd/30_feature/ui_v2/05_WATCHLIST_ANALYSE.md) | Charts, stratégies, scénarios long/short | `GUI2-WATCH-*` |
| [06 — Positions / ordres](prd/30_feature/ui_v2/06_POSITIONS_ORDRES.md) | Paper, broker, stops/KO, actions sécurisées | `GUI2-ORD-*` |
| [07 — Historique et optimisation](prd/30_feature/ui_v2/07_HISTORIQUE_IA_APPRENTISSAGE.md) | Statistiques, diagnostics de stratégie, propositions IA | `GUI2-ANA-*` |
| [08 — Macro et IA](prd/30_feature/ui_v2/08_MACRO_IA.md) | Calendrier, preuves, contextes et coût IA | `GUI2-MAC-*` |
| [09 — Diagnostic / paramètres](prd/30_feature/ui_v2/09_DIAGNOSTICS_PARAMETRES.md) | Santé, alertes, contrôle du risque et configuration | `GUI2-OPS-*` |
| [10 — Internationalisation](prd/30_feature/ui_v2/10_I18N_FR_EN.md) | Traductions Qt et localisation | `GUI2-I18N-*` |
| [11 — Contrats et disponibilité](prd/30_feature/ui_v2/11_CONTRATS_ETATS_DONNEES.md) | DTO, snapshots, états, unités et calculs | `GUI2-DATA-*` |
| [Architecture GUI V2](prd/10_architecture/gui_v2_refactor.md) | Comment transformer le code sans le casser | `GUI2-ARCH-*` |
| [Lotissement R09](prd/02_tasks/phases/R09_gui_v2.md) | Séquence Codex / SR 4.1 | `GUI2-LOT-*` |
| [Consignes Codex](prd/05_coding_agent/gui_v2_codex_guide.md) | Scope, Verification, Activation et interfaces | Exécution |
| [Plan de QA GUI V2](prd/90_quality/gui_v2_qa.md) | Matrice d'acceptation, captures, tests | `AC-GUI2-*` |

## Références visuelles

Images **illustratives**, obtenues par génération graphique. Les chiffres, ordres, cotations et statuts visibles sont des **données fictives**. Les maquettes ne prouvent ni l'existence d'une fonctionnalité, ni sa disponibilité via l'API IG. Les spécifications écrites et les contrats applicatifs priment sur les pixels.

- [Dashboard](prd/95_sources/images/ui_v2/01_dashboard.png)
- [Scanner](prd/95_sources/images/ui_v2/02_scanner.png)
- [Watchlist / Analyse](prd/95_sources/images/ui_v2/03_watchlist_analyse.png)
- [Positions / Ordres](prd/95_sources/images/ui_v2/04_positions_ordres.png)
- [Montage six écrans](prd/95_sources/images/ui_v2/05_montage_ecrans.png)
- [Vues complémentaires](prd/95_sources/images/ui_v2/06_vues_complementaires.png)

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




<!-- SOURCE: docs/prd/30_feature/ui_v2/01_VISION_NAVIGATION.md -->

# 01 — Vision UX, navigation et shell permanent

**Statut :** conception validée en intention ; à implémenter par lots.

## 1. Organisation en deux niveaux

**Niveau 1 : navigation principale par sidebar gauche** (icône + texte, repliable en mode compact) :

1. `Dashboard / Tableau de bord`
2. `Marchés / Scanner`
3. `Watchlist / Valeurs suivies`
4. `Positions & Ordres`
5. `Historique / Analytics`
6. `Macro / IA`
7. `Diagnostics`
8. `Paramètres`

**Niveau 2 : onglets propres à chaque page**, persistants lors des allers-retours, mais ne tenant pas la place du header. La page principale utilise un `QStackedWidget` ou équivalent Qt; les pages métiers et le ruban permanent ne doivent pas être recréés à chaque clic. Une éventuelle vue Expert utilisera des docks détachables pour certains panneaux et une sauvegarde de disposition, sans rendre les docks indispensables à la V2.

## 2. Header / bandeau permanent

De gauche à droite, en une ligne principale sur un écran large : identité TradingIG; badge compte `DEMO` ou `LIVE` et type `CFD`/`BARRIER`/`OPTION`; sélection explicite du compte; **solde / equity / fonds disponibles**; PnL **jour / semaine / mois** (valeur et % si données suffisantes); compteur positions ouvertes; IG REST / streaming / fraîcheur de flux; état IA (prête, travail en cours, résultat frais/périmé, erreur); mode d'exécution ANALYSIS/PAPER/etc.; accès aux notifications et arrêt d'urgence selon capacités existantes.

Le header doit rester clair à 1366 × 768 avec DPI 125 %. En largeur insuffisante, les KPI secondaires basculent dans une seconde ligne ou un panneau « Plus », **jamais** le compte, l'environnement, le mode, les alertes critiques ou la fraîcheur des données.

La barre n'est **pas** une preuve que l'IA est « connectée » : un service cloud qui ne reçoit pas d'appel ne possède pas de socket permanent. Afficher `configurée`, `dernière analyse OK il y a…`, `en cours`, `indisponible`, `quota`, `non configurée`, selon des preuves réelles. Les vérifications ne doivent pas envoyer d'appels IA payants sans consentement. Pour IG, distinguer REST authentifié, Lightstreamer abonné et dernière cotation reçue.

## 3. Bandeau de contexte et status bar

Le `MacroRibbonWidget` existant reste visible dans le shell, sous le header, sous une forme compacte (1 ligne) avec éléments cliquables détaillés dans « Macro / IA ». Badge `INCONNU`/gris obligatoire quand la preuve est manquante. `QStatusBar` accueille détails ponctuels et progression sans cacher les erreurs importantes, qui restent dans l'Inbox d'alertes.

## 4. Comportement des pages et sélection croisée

Sélectionner un marché dans Scanner ⇒ ouvrir « Watchlist / Analyse » sur le même **underlying_id** et le timeframe choisi, sans changer silencieusement le compte ni l'EPIC du produit tradé. Choisir une ligne de position ⇒ ouvrir le détail sur « Positions & Ordres », avec l'identité du compte, du produit et de la position; la sélection ne provoque jamais une action broker. Des liens entre Dashboard, Macro, Analyses et Historique conservent le scope et la période. Le changement de compte invalide les projections anciennes et tous les affichages courtiers restent clairement étiquetés.

## 5. Pages et sous-onglets

| Page | Onglets internes suggérés | Vue par défaut |
|---|---|---|
| Dashboard | Vue d'ensemble · Performance · IA / Amélioration | Vue d'ensemble |
| Scanner | Opportunités · Long · Short · À surveiller · Catalogue IG | Opportunités |
| Watchlist | Graphique · Technique · Analyse IA · Plan de trade · Historique du marché | Graphique |
| Positions / Ordres | Positions · En attente · Historique des ordres · Paper · Alertes | Positions |
| Historique | Journal des trades · PnL · Statistiques · Optimisation IA | PnL |
| Macro / IA | Actualités · Calendrier · Contexte global · Analyses IA | Actualités |
| Diagnostics | Santé services · Flux / quotas · Incidents · Journaux | Santé services |
| Paramètres | Comptes · Marchés · Stratégies · Risque · IA · Notifications · Interface · Avancé | Interface ou Comptes |

## Exigences

- **GUI2-NAV-001** : navigation accessible depuis toutes les pages, raccourcis clavier configurables, état actif visuel et libellés traduits.
- **GUI2-NAV-002** : header visible en permanence ; mode et source de données séparés; alerte critique jamais masquée par l'overflow.
- **GUI2-NAV-003** : pages chargées paresseusement si coûteuses, mais une seule instance des services métier et des connexions externes.
- **GUI2-NAV-004** : retour arrière logique / boutons de navigation sans réinitialiser une analyse ou un graphique.
- **GUI2-NAV-005** : sélection du compte et de l'underlying explicites; aucun héritage ambigu d'un produit ou d'un ordre.
- **GUI2-NAV-006** : taille/fenêtre/dernier onglet persistés, restauration versionnée et fallback sain si disposition obsolète.
- **GUI2-NAV-007** : mode fenêtre normal/maximisé ; pas de perte de contrôle avec un DPI différent ou lors du débranchement d'un second écran.
- **GUI2-NAV-008** : fermer la GUI ne doit pas prétendre maintenir le moteur d'ordres logiciels tant que celui-ci reste dans le même processus ; avertissement si des opérations Paper ou pendings sont actifs.
- **GUI2-NAV-009** : sidebar en mode compact (icônes et infobulles) et mode complet ; la fonctionnalité n'exige pas un serveur ou Electron.

## Critères d'acceptation

- À 1920 × 1080 / 1366 × 768 et DPI 100/125/150 %, les badges de compte et d'exécution restent visibles.
- Un changement de page n'entraîne aucune reconnexion, souscription redondante ou requête OpenAI.
- Un switch DEMO/LIVE invalide les vues du compte précédent sans afficher des positions sous le mauvais environnement.
- Restaurer un layout corrompu affiche la disposition par défaut sans planter ni effacer les réglages de trading.




<!-- SOURCE: docs/prd/30_feature/ui_v2/02_DESIGN_SYSTEM.md -->

# 02 — Design System sombre TradingIG

## Référence visuelle (validée sur l'intention)

**Dashboard souhaité** — [description des maquettes](prd/95_sources/images/ui_v2/REFERENCE_IMAGES.md) (PNG non inclus).

**Scanner souhaité** — [description des maquettes](prd/95_sources/images/ui_v2/REFERENCE_IMAGES.md) (PNG non inclus).

Le style est celui d'un **terminal financier moderne**, sombre, sobre et technique : bleu nuit, surfaces anthracite, bleu/cyan pour la navigation, vert/rouge pour les variations et actions selon leur sens, orange pour la vigilance, gris pour les informations indisponibles. Pas de grands dégradés décoratifs, pas de fonds clignotants permanents.

**Les maquettes sont illustratives** : certaines lignes montrent des ordres IG LIVE ou scores de confiance fictifs, qui ne doivent pas être affichés ou activés en l'absence de données ou de permissions réelles.

## Palette cible et tokens QSS

| Token | HEX proposé | Usage |
|---|---|---|
| `background.base` | `#090F1C` | Fond global |
| `background.sidebar` | `#0C1627` | Barre latérale |
| `surface.1` | `#101D31` | Cartes / tuiles |
| `surface.2` | `#16253A` | Ligne sélectionnée / popover |
| `surface.hover` | `#20324A` | Survol |
| `border.default` | `#2B4057` | Séparateurs subtils |
| `text.primary` | `#EAF1FB` | Titres et contenu |
| `text.secondary` | `#A8BAD0` | Métadonnées |
| `text.muted` | `#75899F` | Aide / désactivé |
| `accent.blue` | `#2C83F5` | Sélection / navigation |
| `accent.cyan` | `#2AC9EC` | Informations techniques |
| `semantic.profit` | `#28D184` | PnL positif / variation positive |
| `semantic.loss` | `#FF606B` | PnL négatif / variation négative |
| `semantic.warning` | `#FFBC53` | Risque / dégradation |
| `semantic.unknown` | `#8995A7` | Inconnu / absent |
| `semantic.critical_bg` | `#84212D` | Alerte critique accessible |
| `semantic.strong_profit_bg` | `#116747` | Surbrillance forte positive |
| `semantic.strong_loss_bg` | `#822936` | Surbrillance forte négative |

Palette **proposée** : ajustements possibles par revue de captures Windows. Ne pas encoder les couleurs dans chaque widget : utiliser `ThemeTokens` et des propriétés Qt `role/state` dans un thème centralisé. Le chart PyQtGraph doit recevoir ses propres couleurs par la même source de tokens.

## Densité et dimensions

- Police sans-serif système Windows (préférence Segoe UI); titres ~16-20 px, texte normal ~12-14 px, données tables ~12-13 px, badges ~11-12 px. Contraste accessible, police sélectionnable dans Paramètres.
- Sidebar déployée ~200-224 px ; repliée ~56-64 px. Header ~64-88 px selon largeur; bandeau macro ~32-40 px; navigation secondaire ~38-44 px.
- Cartes radius 8-12 px, bordures fines 1 px, padding 12-16 px, grille 8 px. Boutons d'action minimum 32 px de haut; zone de clic/icône suffisamment grande pour écran tactile peu prioritaire.
- Tables : lignes 30-34 px, header 34-40 px, zebra très subtil, alignement numérique à droite, colonnes redimensionnables, infobulles pour longues raisons, pas de tronquage silencieux des quantités financières.
- 1920×1080 est une cible de confort; **1366×768** est la cible minimale à vérifier avec zoom Windows 125 %; mode multi-écran et 4K/DPI mixte testés.

## Sémantique des couleurs

Les variations positives de cours et les profits nets sont verts, les négatives rouges. Les signaux `BUY/SELL` portent **leurs libellés explicites** même si une couleur est utilisée. Un short gagnant doit avoir un PnL vert. Ne jamais confondre rouge « prix en baisse » et rouge « perte financière ».

Barème ordinal partagé (déjà présent dans le PRD métier) : **100 exceptionnel/catalyseur**, **75 favorable**, **50 prudence**, **0 défavorable**, **INCONNU sans score**. Les petits badges de scores et leur palette reflètent l'évaluation déterministe; un score 75 n'est **pas** une probabilité de 75 % de réussite. Un pourcentage de confiance IA n'apparaît que si sa provenance et sa définition existent.

### Variations fortes — réglage optionnel

- `highlight_style`: `subtle` (défaut) | `strong` | `off`.
- `highlight_metric`: variation en % sur période choisie pour un marché, PnL net pour une position; ne jamais appliquer une règle financière unique aux deux.
- `positive_threshold_pct`, `negative_threshold_pct`: configurables par famille d'actifs / liste, valeurs initiales UI proposées ±1,00 % sur variation journalière **à valider** ; pas de catégorisation de risque automatique par ces seuils.
- Pour `strong` : fond vert foncé / rouge foncé, texte blanc à contraste suffisant, icône ▲/▼; surbrillance uniquement de la cellule ou petit badge, jamais de la ligne entière par défaut.

## Composants standards

- `AccountStatusBar` : badges DEMO/LIVE/compte + soldes et états de connectivité.
- `NavSidebar` : icône monochrome + titre traduit + sélection.
- `KpiCard` : titre, valeur, évolution, période, tooltip sur provenance, état `N/A` si absent.
- `FinancialTimeSeriesChart` : barres PnL ou courbe equity alignées sur les mêmes périodes.
- `MarketTable` / `PositionTable` : tri, filtres, sélection par identifiant stable, pas par index.
- `ScoreChip` : ordinal/INCONNU et provenance; la couleur seule ne suffit pas.
- `DataFreshnessPill` : `LIVE`, `STALE`, `WARMING_UP`, `DATA_GAP`, `N/A`.
- `ErrorBanner` / `ActionConfirmationDialog` : affichage persistant des erreurs importantes et récapitulatif des conséquences.
- `AnalysisEvidenceCard` : auteur/provider, période, timestamp, sources et limites.

## Exigences

- **GUI2-DS-001** : thème sombre conforme aux références, totalement centralisé, sans QSS dispersé.
- **GUI2-DS-002** : couleurs et texte/icone redondants pour déficience de perception des couleurs.
- **GUI2-DS-003** : état `disabled/loading/error` cohérent pour chaque contrôle, sans action factice.
- **GUI2-DS-004** : accentuation forte paramétrable, jamais une promesse d'opportunité ou de rentabilité.
- **GUI2-DS-005** : nombres alignés, unités explicites, arrondis de présentation sans altérer `Decimal` métier.
- **GUI2-DS-006** : aucune donnée mockée en production sous une apparence de donnée réelle ; mode démo visuelle explicitement étiqueté pour tests seulement.
- **GUI2-DS-007** : captures comparatives sur Windows et revue humaine avant validation esthétique.

## Exemple d'amorce QSS (indicatif)

```css
QMainWindow, QWidget#AppShell { background: #090F1C; color: #EAF1FB; }
QFrame[role="panel"] { background: #101D31; border: 1px solid #2B4057; border-radius: 10px; }
QPushButton[role="primary"] { background: #2C83F5; color: #FFFFFF; border-radius: 6px; padding: 6px 12px; }
QPushButton[role="primary"]:hover { background: #4695FF; }
QPushButton[role="primary"]:disabled { background: #304158; color: #8995A7; }
QTabBar::tab:selected { border-bottom: 2px solid #2C83F5; color: #FFFFFF; }
```

Cette feuille est une **référence partielle**, pas un thème complet à copier telle quelle; éviter de casser les textes/axes/overlays de PyQtGraph ou les états standard Qt.




<!-- SOURCE: docs/prd/30_feature/ui_v2/03_DASHBOARD.md -->

# 03 — Dashboard / Tableau de bord

**Maquette dashboard** — [description des maquettes](prd/95_sources/images/ui_v2/REFERENCE_IMAGES.md) (PNG non inclus).

## Finalité

Première page à l'ouverture, **synthèse de la performance du compte sélectionné** et de la situation à surveiller. Le dashboard ne doit pas exiger de charger l'intégralité du catalogue IG ou de recalculer tous les signaux.

## A. Vue d'ensemble — disposition proposée

1. Rangée de `KpiCard`: equity/solde, fonds disponibles, PnL J/S/M, positions ouvertes, win rate, profit factor, drawdown (afficher `N/A` si non calculable).
2. Zone « Performance » : **deux graphiques synchronisés sur la même fenêtre et granularité**. À gauche histogramme du PnL **en EUR (ou devise du compte) ou en %**, à droite **courbe du solde/equity du compte**; choix `Jour / Semaine / Mois / Année`, sélecteur de plage de dates et synchronisation curseur et zoom X.
3. Zone « Statistiques ordres / trades » : positions ouvertes, ordres en attente, ordres acceptés/rejetés, trades clôturés gagnants/perdants/nuls, taux de réussite calculé seulement sur trades clôturés avec résultat connu, expectancy et R/R si connu.
4. Zone « IA — bilan et pistes d'amélioration » : tendances observées, risques d'échantillon, propositions *non appliquées*, bouton vers Historique/Optimisation.
5. Zone « Macro / actualités / calendrier » : 3–6 annonces majeures, heure locale, impact, actifs exposés, fraîcheur et source; clic vers Macro/IA.
6. Tableau « Positions ouvertes » : informations essentielles live/Paper à l'écran, tri PnL ou risque, accès détail; taille adaptable, maximum visuel ~8 lignes avec scroll, sans cacher des positions dans les KPIs.

Sous-onglets : `Vue d'ensemble`, `Performance`, `IA / Amélioration`. Les KPI d'en-tête global sont persistants hors dashboard.

## B. Définition financière / source de vérité

- Toute mesure appartient à un **compte**, une devise, un **mode** (`PAPER`, `BROKER`), une période, un instant de calcul et une source. Une vue mixte Paper+Broker nécessite une action volontaire distincte et un marquage explicite; **pas de somme implicite**.
- `PnL net période` : PnL réalisé sur trades clôturés imputés à la période **après frais et financement connus**; afficher un second indicateur latent séparé plutôt qu'y ajouter arbitrairement le PnL ouvert. Les frais manquants rendent le « net certifié » indisponible ou « estimé ».
- `Solde` : balance cash broker vs `Equity` (balance + PnL latent, si définition du fournisseur confirmée). Choix courbe `Equity`/`Solde` explicite; affichage des valeurs historiques uniquement à partir de **snapshots horodatés** ou d'une reconstitution auditable; pas de ligne historique factice obtenue depuis la seule valeur courante.
- `PnL % période` : `PnL net période / equity de début de période * 100` uniquement si ces valeurs sont établies et qu'aucun flux externe (dépôt/retrait) ne fausse la comparaison; sinon `N/A` ou méthode TWR/MWR ultérieure clairement indiquée.
- Aucun passage automatique d'un PnL **réalisé** à un PnL « total » sans changement d'étiquette; les données multidevises exigent taux de conversion daté/traçable ou restent séparées par devise.
- Stats : `ordre accepté/rejeté` = résultat technique d'exécution ; `trade gagnant/perdant` = résultat économique. Un ordre accepté peut finir perdant. `win_rate` exclut les trades ouverts et traite les nuls dans une catégorie explicite.
- La période du graphique barres et de la courbe equity est commune : si une partie de la série manque, afficher un trou et `Données insuffisantes`, jamais compléter par des points inventés.

**Implémentation existante vérifiée** : `services/analytics_service.py::aggregate_realized_pnl()` sait regrouper du PnL réalisé par jour/semaine/mois/année et devise; cela **ne fournit pas** à lui seul la courbe d'equity historique, le taux de réussite ni des performances LIVE vérifiées. Codex doit créer une projection dédiée, sans transformer le module de calcul existant en widget.

## C. Interaction

- Changement granularité J/S/M/A ⇒ actualiser simultanément les deux graphiques, stats et dates.
- Changement devise EUR/% ⇒ conserver les dates/zoom; afficher la formule dans infobulle; si capital de début absent, `N/A` en pourcentage.
- Cliquer une barre ⇒ filtrer la table des trades sur la période; cliquer un point equity ⇒ afficher la date et la provenance du snapshot.
- Choisir une position ⇒ ouvrir détail Positions; clic événement ⇒ ouvrir contexte Macro; clic suggestion IA ⇒ ouvre une proposition en revue, sans appliquer.
- Absence d'historique ⇒ état vide guidant la collecte et la validation, pas de données démo maquillées.

## Exigences

- **GUI2-DASH-001** : tableau de bord par compte et mode, avec période explicitement visible.
- **GUI2-DASH-002** : histogramme PnL EUR/% et ligne solde/equity synchronisés temps/zoom/curseur.
- **GUI2-DASH-003** : calculs financiers tracés aux événements et snapshots; aucune invention de capital passé.
- **GUI2-DASH-004** : séparation ordres techniquement réussis et trades financièrement gagnants.
- **GUI2-DASH-005** : positions ouvertes mises à jour avec prix valide, latence/fraîcheur et contrôles de protection; clic détail.
- **GUI2-DASH-006** : actualités et événements à venir par source / impact et horodatage.
- **GUI2-DASH-007** : suggestions IA d'optimisation consultatives, versionnées, jamais auto-appliquées.
- **GUI2-DASH-008** : recalcul non bloquant et rafraîchissement incrémental; dashboard fonctionnel avec historique incomplet.
- **GUI2-DASH-009** : affichage « aucune donnée / impossible à calculer » pour les statistiques non encore disponibles.

## Critères d'acceptation

Un jeu test avec trois jours (un jour gagnant, un jour perdant, un jour sans trade) rend les barres correctes et les mêmes dates sur la courbe equity; changer en % produit `N/A` si le capital initial est absent. Les ordres rejétés ne sont jamais comptés comme trades perdants. Un compte DEMO et une session Paper ne fusionnent pas leur PnL sans demande explicite.




<!-- SOURCE: docs/prd/30_feature/ui_v2/04_SCANNER_CATALOGUE.md -->

# 04 — Marchés / Scanner et catalogue IG

**Maquette scanner** — [description des maquettes](prd/95_sources/images/ui_v2/REFERENCE_IMAGES.md) (PNG non inclus).

## Objectif

Faire du scanner la **porte d'entrée des opportunités**, sans confondre le suivi des *marchés de référence*, l'inventaire des *produits IG* et les *possibilités réelles d'exécution*.

## A. Cinq sous-onglets

`Opportunités` (défaut), `Long / Haussier`, `Short / Baissier`, `À surveiller`, `Catalogue IG`.

Les quatre premiers lisent des projections du **scanner par sous-jacent**. Le catalogue montre **tous les produits découverts et filtrables** à la date du dernier inventaire, même s'ils ne possèdent pas un flux direct exploitable; ne jamais annoncer « temps réel pour tous » si IG limite les abonnements. Seules les références suivies et les produits bénéficiant de droit de flux peuvent être souscrits selon un budget de streaming configuré.

## B. Tableau scanner marchés

Colonnes obligatoires : favori, marché/ID de référence, classe d'actif, dernier cours et devise/unité, variation absolue, variation % et fenêtre, source/âge de cotation, **score technique**, **contexte/score IA**, prochain événement significatif (heure/impact), risque de marché, `LONG / SHORT / NEUTRE / NO_TRADE / INDISPONIBLE`, raison synthétique et dernière évaluation. En expansion facultative : signaux par stratégie, R/R, coûts, qualité OHLC, consensus, bornes de validité, sources.

Les colonnes sont réordonnables, redimensionnables et masquables, avec profils de présentation sauvegardés. Tri stable `score DESC`, `variation`, `heure`, `nom`; les filtres ne détruisent pas l'état du modèle. Le tableau conserve une ligne par marché configuré, même si les données n'ont pas suffi au calcul — statut et raison obligatoires.

## C. Catalogue de produits IG

Colonnes : nom IG, `product_epic`, famille, sous-jacent **confirmé/absent**, environnement/compte associé, direction d'exposition, sens d'ordre disponible, bid/ask/spread, variation, devise, `KO`/strike/échéance si applicable, taille min, statut IG, âge dernière cotation, score technique et sentiment **seulement si hérités d'un binding validé**. Le score de l'underlying doit être intitulé `Contexte du marché de référence`, jamais comme un score du produit dérivé à coût identique. Les données de risque/cout/prime propres au produit ne sont pas héritables.

La recherche ciblée IG actuelle peut ajouter des produits temporairement à la session, distincts du catalogue enregistré : afficher `Découvert en session / non confirmé`. Une correspondance EPIC déduite d'un nom n'est jamais suffisante pour projeter scores et IA. Une Barrière CALL/PUT n'implique pas un ordre BUY/SELL automatiquement.

## D. Scores, fraîcheur et couleurs

Les badges de **composantes** respectent le barème qualitatif métier `100/75/50/0/UNKNOWN`. Le `score global` utilise les pondérations existantes (**30 technique / 15 contexte / 20 R:R / 15 risque marché / 10 coûts / 10 qualité données**) seulement si les entrées indispensables existent et les vetos sont satisfaits. Une analyse IA favorable ne crée pas par compensation un score technique artificiel.

Pour l'affichage du score IA, deux concepts distincts : **contexte directionnel** (`bullish/bearish/neutral/unknown`) et **évaluation de qualité/confiance**, cette dernière calculée ou présentée uniquement si le contrat l'autorise. Les tableaux ne doivent pas transformer librement une confidence LLM en « score de profit ». La confiance IA est une évaluation interne non calibrée de la qualité de sortie, pas une probabilité réelle de réussite.

Variation positive (cours) : texte vert, négative : rouge; mode surbrillance forte en fond coloré optionnel, seuils paramétrables. Un cours en baisse peut être une **opportunité short**, pas un échec. `INCONNU` : gris neutre avec infobulle d'explication.

## E. Mise à jour et limites

- Liste initiale recommandée : US Tech 100, France 40, Allemagne 40, Or Spot, Pétrole US; configuration utilisateur sans plafond fixe produit. D'autres marchés accessibles par recherche/catalogue.
- Service d'analyse multi-marchés existant `ScannerRuntimeBatchService`; le runtime GUI appelle aujourd'hui une mise à jour essentiellement manuelle, donc créer une **politique de scheduling** périodique *avec budget de données* et possibilité pause / rafraîchir. Le scheduler ne crée aucun ordre.
- Rafraîchir les cellules sur changement effectif avec coalescing (p.ex. 250–1000 ms UI), tout en respectant la cadence réelle et les quotas. En absence de nouveau prix, ne pas rafraîchir artificiellement l'heure du prix.
- Les listes peuvent contenir plusieurs centaines de produits : modèle Qt paginé/virtualisé via `QAbstractTableModel`, cache borné, tri/filter `QSortFilterProxyModel`; jamais plusieurs centaines de widgets en lignes recréés à chaque tick.
- Une souscription streaming refusée donne `NO_STREAM_PERMISSION` ou `NOT_SUBSCRIBED`, avec timestamp du dernier snapshot s'il existe. Les données de cotation dérivée ne prouvent pas une OHLC sous-jacente correcte.

## F. Actions

Double-clic marché ⇒ page Watchlist / Analyse sur marché de référence; bouton étoile ⇒ ajouter/retirer favoris; clic événement ⇒ calendrier; clic source ⇒ détail provenance; clic produit ⇒ fiche produit puis ticket Paper *seulement* si ses contraintes sont qualifiées. Aucune ligne n'active un ordre au simple clic.

## Exigences

- **GUI2-SCAN-001** : tableau multi-marchés classé actualisable automatiquement avec pause et statut.
- **GUI2-SCAN-002** : tous les marchés configurés restent visibles avec raison d'indisponibilité plutôt que disparition silencieuse.
- **GUI2-SCAN-003** : scores techniques/IA/contextuels séparés, ordinaux non probabilistes et données manquantes grises.
- **GUI2-SCAN-004** : long/short/à surveiller avec raisonnement explicitement affiché et vetos.
- **GUI2-SCAN-005** : catalogue IG distinct des sous-jacents, recherche/filtres/colonnes, avec respect des droits et quotas.
- **GUI2-SCAN-006** : binding EPIC exact requis pour toute projection de contexte du sous-jacent vers produit.
- **GUI2-SCAN-007** : rendu incrémental scalable, tri/filtre et sélection stables en streaming.
- **GUI2-SCAN-008** : surbrillance forte optionnelle et sans confusion entre sens de marché et succès d'un trade.
- **GUI2-SCAN-009** : horodatages de prix, sentiment et signal distincts et conservés durant les pannes.
- **GUI2-SCAN-010** : états d'erreur liés aux permissions/quotas sans appels REST en boucle.

## Acceptation

Sur 500+ produits de test, le tableau peut être scrollé et filtré sans latence manifeste ni requête IG par cellule. Un binding invalide laisse le score IA `NOT_APPLICABLE`. Une perte de flux rend la ligne stale sans avancer l'horodatage. Un short sur prix en baisse doit afficher direction `SHORT` et variation rouge, **sans** en déduire un PnL négatif.




<!-- SOURCE: docs/prd/30_feature/ui_v2/05_WATCHLIST_ANALYSE.md -->

# 05 — Watchlist et analyse détaillée d'un marché

**Maquette Watchlist / Analyse** — [description des maquettes](prd/95_sources/images/ui_v2/REFERENCE_IMAGES.md) (PNG non inclus).

## Mission

Permettre de suivre rapidement 4–5 marchés (par défaut) et d'obtenir une analyse approfondie en changeant de sous-onglet sans perdre le graphique. L'onglet `Graphique` constitue l'espace central de travail; l'IA et le plan de trade sont des panneaux secondaires facultatifs / onglets.

## A. Structure

**Colonne gauche** : watchlist, étoiles/favoris, sous-jacent, dernier cours, variation, état du flux, graphe miniature si coût/performance raisonnable. `+ Ajouter` ouvre recherche catalogue et affectation éventuelle d'un binding; aucune attribution implicite de droit de flux.

**Barre du marché sélectionné** : nom et canonical ID, ticker IG de référence s'il existe, état marché, date de dernière cotation, bid/ask, spread, jour haut/bas, statut OHLC (défaut `WARMING_UP` si insuffisant).

**Centre** : graphique PyQtGraph existant, chandeliers, croix OHLC et zoom, 1/5/15/30 min, H1/H4, un jour si le fournisseur de données l'autorise. EMA, SMA, bandes Bollinger, niveaux support/résistance, entrée, stop, KO, objectif superposables **individuellement**. Pour RSI/MACD/ATR, privilégier des sous-panneaux synchronisés en axe temporel pour ne pas déformer le prix.

**Sous-onglets** : `Graphique`, `Analyse technique`, `Analyse IA`, `Plan de trade`, `Historique`. En mode normal, un petit volet latéral `Résumé rapide` peut exposer 3-5 indicateurs; mode Expert peut détacher l'IA ou le plan de trade en dock. Le chart doit rester plus grand que les panneaux périphériques.

## B. Analyse technique

Table de l'indicateur, valeur, unité, période, seuils et statut; signaux des stratégies TREND_FOLLOW, BREAKOUT, PULLBACK et EVENT_DRIVEN si valide. Chaque indicateur porte source de bougies, timeframe, nombre de bougies clôturées utilisées, âge, continuité, paramètres, raison `WARMING_UP`/`INVALID`. Multi-timeframe explicitement séparé, pas de « RSI H1 » calculé sur M1 en faisant semblant.

Les signaux affichent direction, niveaux, horizon, conditions d'invalidation, source, stratégies concordantes/divergentes, timestamp et expiration. `NO_TRADE` explicité et mis en évidence lorsqu'aucune stratégie ne passe les filtres.

## C. Analyse IA

Résumé en français ou anglais selon UI (contenu externe peut rester dans la langue retournée avec indication), biais directionnel, niveau de risque, confiance source, liste horodatée des preuves et liens vérifiables. Bouton `Analyser à nouveau` avec indication que cela peut coûter des appels OpenAI, progress et budget; aucun appel automatique provoqué par un simple changement d'onglet.

La recherche web IG/OpenAI du produit courant reste consultative. Une analyse peut être disponible en contexte macro mais **non applicable** au produit dérivé faute de binding exact. `STALE` après expiration (10 min dans le parcours actuel), `UNKNOWN` en l'absence d'analyse.

## D. Plan de trade

Afficher **trois résultats distincts** :

- scénario **haussier / LONG** : déclencheur, entrée ou zone, invalidation, objectif, stop structurel/ATR, R/R attendu, éventuel produit dérivé compatible ;
- scénario **baissier / SHORT** : mêmes champs, avec invalidation au-dessus et objectifs en dessous ;
- **NO_TRADE** : conditions bloquantes ou données manquantes.

Le libellé LONG/SHORT exprime la position économique sur le marché sous-jacent. Une option/barrière avec exposition baissière peut s'acheter à l'ouverture, donc l'**ordre IG BUY/SELL** doit être calculé séparément en fonction du contrat documenté et d'une confirmation humaine. Ne pas copier automatiquement une décision SHORT dans un champ `SELL` pour un produit dérivé.

Le bouton `Préparer ticket Paper` ouvre un ticket pré-rempli **en brouillon**, fait repasser les contrôles RiskEngine et exige confirmation explicite. Il ne crée pas d'ordre. Si frais/KO/cotation/FX/lot minimum manquent : `Non évaluable` et suggestions de données à fournir, pas d'ordre.

## E. Détail historique du marché

Journal des signaux et trades sur ce sous-jacent, taux de réussite par stratégie si nombre et qualité des observations suffisants, analyse des faux signaux, coûts, données manquantes. Séparer backtests (simulation) et trades Paper/LIVE réels.

## Exigences

- **GUI2-WATCH-001** : watchlist configurée et identités de marchés stables, un seul marché actif à la fois dans la vue standard.
- **GUI2-WATCH-002** : réutilisation du moteur PyQtGraph et des indicateurs/services existants, sans refaire les calculs dans les widgets.
- **GUI2-WATCH-003** : overlay paramétrable et panneaux indicateurs synchronisés, performances UI préservées.
- **GUI2-WATCH-004** : valeurs/stratégies explicables, complétude OHLC et dates visibles.
- **GUI2-WATCH-005** : vue IA affichant périmètre, sources, fraîcheur, coûts potentiels, statut et limites.
- **GUI2-WATCH-006** : plans LONG, SHORT et NO_TRADE en parallèle, séparés du sens d'ordre du contrat IG.
- **GUI2-WATCH-007** : clic vers brouillon Paper uniquement si données et règles déterministes passent les gates.
- **GUI2-WATCH-008** : le changement de marché ne recycle pas silencieusement l'IA ou les prix de l'instrument précédent.
- **GUI2-WATCH-009** : indication du nombre de bougies nécessaires à la disponibilité des indicateurs, sans forcing d'historique IG.

## Critères d'acceptation

Un M1 incomplet ne devient pas H1 exploitable. Une série session-only après reboot commence à `WARMING_UP`. Une analyse IA d'un CAC 40 LIVE ne s'affiche pas comme applicable à une Barrière DEMO non liée. Un plan SHORT sur barrière PUT ne remplit pas `SELL` sans résolution explicite du produit.




<!-- SOURCE: docs/prd/30_feature/ui_v2/06_POSITIONS_ORDRES.md -->

# 06 — Positions, ordres, Paper et contrôles de risque

**Maquette Positions et ordres** — [description des maquettes](prd/95_sources/images/ui_v2/REFERENCE_IMAGES.md) (PNG non inclus).

## Objectif

Un tableau central lisible **en temps réel quand le flux le permet** pour surveiller toute exposition ouverte, avec les niveaux de protection et les actions disponibles. Le tableau reste **informateur** quand l'ordre broker est bloqué ; l'apparence d'un bouton ne doit jamais autoriser une fonction non qualifiée.

## A. Sous-onglets

`Positions ouvertes` (défaut), `Ordres en attente`, `Historique des ordres`, `Trading Paper`, `Alertes`.

### Positions ouvertes

Colonnes obligatoires : environnement et compte, `position_id` IG ou Paper, marché/produit/EPIC, type (CFD/Barrière/Option), exposition LONG/SHORT, **sens d'ordre d'ouverture** BUY/SELL, quantité et unité, prix d'entrée, dernier prix de valorisation et âge, PnL net/estimé devise et %, stop loss actif et source broker/logiciel, KO si applicable, limite/TP, risque courant, état (`OPEN`, `PROTECTED`, `TRAILING`, `CLOSING`, `UNCERTAIN`, `CLOSED`), ouverture, statut de synchronisation broker. Les colonnes secondaires peuvent être masquées, mais les niveaux et l'identité ne doivent pas disparaître dans une infobulle.

Le résumé en haut inclut nombre de positions, exposition brute, PnL latent (estimé ou réel et devise), perte restante théorique sous stop/KO **avec caveat slippage/gap**, nombre de protections non confirmées. Tout prix absent marque le PnL comme stale/indisponible.

### Ordres en attente

Séparer `NATIF_IG` et `LOGICIEL_LOCAL` ; déclencheur, conditions, expiration, dernière validation, état, source de prix, confirmation humaine requise, contraintes de réévaluation. Un pending local cesse d'être fiable si le programme ne tourne plus ou si le flux est stale ; l'interface l'annonce sans ambiguïté.

### Trading Paper

Réutiliser **PaperTicketWidget**, **PaperPortfolioWidget**, **PaperSessionService** et les safeguards existants. Les actions locales `ouvrir`, `resserrer stop`, `fermer`, `sauvegarder`, `restaurer` restent explicites. Ne pas changer la politique actuelle de restauration : **aucune base Paper automatiquement ouverte au démarrage**, récupération seulement sur action utilisateur tant que cette décision n'a pas été révisée.

### Historique et alertes

Afficher confirmation/rejet broker, changements de stop, coûts connus, latence, corrélation, provenance et horodatage; un ordre `UNCERTAIN` impose réconciliation avant nouvelle action. Les alertes restent dans un journal même si une notification externe échoue.

## B. Actions et autorisations

Trois niveaux : consulter, préparer, exécuter. Les composants ne décident pas eux-mêmes de l'autorisation : demander à une **façade applicative** l'état des capacités et le résultat du RiskEngine. Un bouton visible en mode `PAPER` ouvre une simulation locale uniquement; un bouton broker `LIVE` ne doit pas être généré ou activé tant que la capacité correspondante et l'autorisation utilisateur ne sont pas établies. Test CFD DEMO borné historique ≠ approbation générale.

Le dialogue de confirmation doit préciser : **source du prix**, environnement, compte, marché, produit exact, direction économique, `order_side`, quantité, stop, TP, KO, frais, perte estimée et éventuelle différence avec la perte maximale KO, timestamp de validation. En contexte `STALE` ou risque non calculable, aucun bouton d'exécution valide.

## C. Gestion des stops

Afficher la valeur *confirmée par le broker* et, si elle diffère, la valeur *proposée/pendante*. Ne pas afficher `Stop sécurisé` tant qu'une confirmation broker (ou mise à jour Paper attestée) ne l'établit. Stop d'un long ne se baisse pas automatiquement; stop d'un short ne monte pas automatiquement. Le break-even « net de frais » ne garantit jamais risque zéro (gap, slippage, défaillance de protection, KO).

## Exigences

- **GUI2-ORD-001** : identités compte/environnement/exécution visibles sur toutes lignes et actions.
- **GUI2-ORD-002** : actualisation prix et PnL non bloquante et âge du prix contrôlé.
- **GUI2-ORD-003** : stop/TP/KO simultanés et différenciés, statut confirmé/proposé/pending.
- **GUI2-ORD-004** : stockage et présentation distincts des positions IG et Paper; aucune agrégation ambiguë.
- **GUI2-ORD-005** : impossibilité pour GUI de contourner le RiskEngine et les droits/permissions API.
- **GUI2-ORD-006** : ordres en attente natifs et locaux clairement séparés; panne/fermeture application détectée.
- **GUI2-ORD-007** : reprise des fonctionnalités Paper vérifiées, sans régression des snapshots/restauration explicite.
- **GUI2-ORD-008** : confirmations/correlation_id/état incertain et journalisation de chaque action.
- **GUI2-ORD-009** : boutons `Modifier`/`Clôturer` désactivés avec explication en l'absence de chemin broker autorisé.
- **GUI2-ORD-010** : shortlist des positions du Dashboard synchronisée avec la même source de vérité.

## Acceptation

En `IG LIVE` données + `PAPER` exécution, la vue doit marquer toutes les positions simulées `PAPER` et les boutons n'appellent jamais `IGRestAdapter.create_otc_position`. Un stop non confirmé ne change pas d'affichage « actif ». Déconnexion avec pendings locaux ⇒ bannière visible. Restauration Paper avec doublon ⇒ confirmation et prévention de l'écrasement, conformément aux règles existantes.




<!-- SOURCE: docs/prd/30_feature/ui_v2/07_HISTORIQUE_IA_APPRENTISSAGE.md -->

# 07 — Historique, statistiques et IA d'optimisation

## Objectif

Exploiter les transactions passées pour quantifier la performance et construire un **processus d'amélioration contrôlé**. « L'IA apprend des trades » signifie ici : exploiter un dataset historique fiable, repérer des régularités/hypothèses et proposer des changements à **valider et tester**. Cela n'autorise pas un LLM à modifier silencieusement les paramètres ou la politique de risque.

## Pages / sous-onglets

`Journal des trades`, `PnL`, `Statistiques`, `Optimisation IA`.

### Journal des trades

Table filtrable par compte, Paper/Broker, marché, produit, stratégie, direction, période, résultat et qualité de données. Un trade possède un identifiant stable, entrées/sorties, frais, MFE/MAE si disponibles, raison d'entrée et sortie, version des paramètres, version de stratégie, contexte technique/macro/IA et snapshots horodatés. Les propositions refusées et les sorties `NO_TRADE` doivent être interrogeables séparément pour analyser la qualité des opportunités manquées.

### Performance et statistiques

Graphiques de résultats nets périodiques, courbe equity si snapshots réels, drawdown, cumul R, résultats par marché/stratégie/sens/timeframe/heure de la journée, coûts, slippage, expectancy, profit factor, proportion de trades gagnants/perdants/nuls et taille de l'échantillon. Une vue « comparaison de stratégies » nécessite au moins un jeu de données et un intervalle communs.

Aucune statistique de win rate ne doit utiliser des événements en attente ou des ordres refusés comme des pertes économiques. Une série à faible effectif est étiquetée « exploratoire ». Les analyses paper et live sont identifiées et comparées, jamais fusionnées par défaut.

### Optimisation IA — workflow gouverné

1. L'utilisateur sélectionne **scope, période, stratégie, marché, mode et dataset** et vérifie la complétude des données.
2. Un diagnostic déterministe produit statistiques, ventilations et écarts avec la configuration actuelle.
3. Sur action explicite, l'IA examine **des agrégats et faits anonymisés/consentis**, propose des hypothèses : « filtrer les trades proches d'un événement », « réduire exposition durant haute volatilité », « comparer deux trailing stops », etc.
4. Chaque hypothèse devient un `OptimizationProposal` avec **paramètre cible**, ancienne/nouvelle valeur envisagée, hypothèse, preuves, effectif, période, biais possibles, niveau de confiance, risques, coût de recalcul, statut `DRAFT`.
5. Une action `Tester en replay` lance la simulation future-blind avec jeux **train/validation/test chronologiques et versionnés**. Des résultats de backtest non testés hors-échantillon ne sont pas considérés comme acceptés.
6. La page affiche **avant/après**, distribution des résultats (pas seulement gain moyen), drawdown, coûts, sensibilité, test hors échantillon et incertitudes.
7. **Validation humaine explicite** pour proposer une modification de profil de stratégie/risk config; nouvelle version enregistrée et possibilité de rollback. Changement pouvant augmenter le risque journalier/max trade interdit par la simple recommandation IA; nécessite parcours de sécurité dédié.
8. L'adoption et son résultat ultérieur sont suivis, puis la proposition peut être rejetée, retirée ou réévaluée.

Un modèle LLM général ne s'« entraîne » pas automatiquement parce qu'on lui fournit un journal. Le système peut utiliser une boucle d'évaluation et, dans une phase ultérieure, un modèle statistique entraînable si l'historique, les licences et la quantité de données le permettent. Aucun apprentissage continu sur un compte LIVE par ajustement opaque.

## Cautions et confidentialité

- Consentement à l'envoi des données de trading à une IA externe; les IDs de compte, clés, détails personnels sont retirés; les positions/prix/horodatages eux-mêmes peuvent être sensibles — option d'analyse locale déterministe sans envoi externe.
- Conservation de `provider_id`, `model_id`, `prompt_version`, fenêtre temporelle et coût estimé/réel pour les analyses IA.
- Une « amélioration de +X % » ne peut être affichée comme fait que si issue d'une comparaison chiffrée et étiquetée `simulation / hors échantillon / live observé`.
- Alertes anti-overfitting et survivorship bias, look-ahead bias, sélection biaisée et changement de régime; comparer à un baseline et au hasard si pertinent.
- Le moteur de trading reste protégé par les règles déterministes et ne consomme jamais directement du texte libre comme signal d'ordre.

## Exigences

- **GUI2-ANA-001** : journal filtrable, export CSV/JSON expurgé, provenance et distinction Paper/Broker.
- **GUI2-ANA-002** : métriques correctement définies par compte/devise/mode, avec effectif et dates.
- **GUI2-ANA-003** : suivi des paramètres historiques, versions de stratégie et coûts/frais de chaque scénario.
- **GUI2-ANA-004** : `OptimizationProposal` typée, auditable, non exécutable, avec preuves et hypothèses.
- **GUI2-ANA-005** : aucune modification de configuration par simple réception d'une réponse OpenAI.
- **GUI2-ANA-006** : validation hors échantillon et politique de rollback avant activation de modification.
- **GUI2-ANA-007** : consentement explicite avant transmission d'historique de transactions externe.
- **GUI2-ANA-008** : gestion des datasets incomplets ou non versionnés avec état `INSUFFICIENT_EVIDENCE`.
- **GUI2-ANA-009** : séparation des avis IA, résultats réels, résultats Paper et backtests.

## Acceptation

Une suggestion IA « augmenter le risque par trade » n'affecte aucun paramètre sans validation. Un gain hypothétique sans dataset validé est affiché « Hypothèse non testée ». Le projet peut désactiver le provider IA et conserver toutes les statistiques déterministes.




<!-- SOURCE: docs/prd/30_feature/ui_v2/08_MACRO_IA.md -->

# 08 — Macro, actualités financières et intelligence artificielle

## Mission

Présenter une vue cohérente des facteurs macroéconomiques / géopolitiques, des événements à venir et des analyses IA tout en assurant la **traçabilité, fraîcheur, portée et droit d'utilisation** des sources.

## Sous-onglets

1. `Actualités & contexte` : titres, source officielle ou provider autorisé, publication/collecte, type, marché concerné, niveau d'importance, résumé, lien et état de vérification.
2. `Calendrier économique` : date/heure locale, zone/pays, publication, consensus/précédent/réalisé **si fournisseur les délivre**, classification de l'impact, marchés concernés et fenêtre de vigilance. Rechercher/filtrer par date/pays/importance.
3. `Contexte global` : régime risk-on/off, taux, USD, VIX (si réellement fourni), or, pétrole, géopolitique, sources, timestamp et bandeau d'état global. Pas de fausses données si seulement les RSS Fed/BCE existent.
4. `Analyses IA` : historique de snapshots, product/underlying scope, modèle, prompt, biais, risque, confidence, sources et expiration, coût et consentement aux appels.

## Qualité et absence d'information

Le projet dispose aujourd'hui de collecte de métadonnées Fed/BCE et d'un adaptateur Trading Economics validé hors ligne sans abonnement connu; leur santé de service ne constitue pas un sentiment directionnel. La recherche web OpenAI est consultative, manuelle, structurée ensuite dans un snapshot d'analyse séparé. Les analyses multi-marchés automatiques coûtent potentiellement des requêtes supplémentaires : **pas d'activation par défaut** dans la nouvelle GUI. Les abonnements, licences, quotas et fréquence sont configurables et contrôlés.

Les badges `green/yellow/red/gray` concernent **l'impact/risque** et pas automatiquement la hausse/baisse du marché; deux indicateurs distincts : `event_risk` (sévérité) et `market_bias` (direction).

## Workflow IA

- `Tester configuration` indique si l'API et son modèle peuvent être utilisés, uniquement via un probe explicitement demandé si cela déclenche coût réseau.
- `Lancer une analyse` : marché/périmètre choisi, synthèse des sources et coût potentiel estimé, confirmation si nécessaire; lancement en worker, annulation UI sûre, statut et résultat.
- `Analyse périodique` : profil de fréquence, budget mensuel/journalier, marchés autorisés, nombre max de recherches, consentement, dates d'expiration; par défaut désactivé pour web/IA multi-marchés.
- `Différences` : macro versus IA, conflit de signaux, désaccord entre stratégie technique et contexte (étiquette prudence, pas arbitrage aveugle du LLM).
- L'intégration scanner/plan de trade reste **consultative**, jusqu'à validation explicite des règles d'entrée déterministes.

## Exigences

- **GUI2-MAC-001** : calendrier et sources avec heure locale/date UTC interne, visibilité de l'impact et filtre.
- **GUI2-MAC-002** : distinction information collectée, analyse IA et fait marché vérifié.
- **GUI2-MAC-003** : contrôles de fraîcheur, expiration, sources et applicable/non applicable par produit.
- **GUI2-MAC-004** : aucun appel IA payant causé par le seul rendu d'un widget.
- **GUI2-MAC-005** : nombre d'appels, coût, budget, statut et autorisation visibles dans paramètres / diagnostics.
- **GUI2-MAC-006** : risque événementiel distinct de sentiment directionnel, dans le dashboard et le scanner.
- **GUI2-MAC-007** : analyse IA lisible en français/anglais selon possibilité, avec traduction des labels UI indépendamment du texte externe.
- **GUI2-MAC-008** : données absentes = inconnu / not applicable sans scores fictifs.

## Acceptation

Sans API de calendrier active, l'onglet affiche l'absence et une procédure de configuration sans inventer CPI/NFP datés. Une recherche web manuelle produit une trace de modèle, source, scope et expiration. Changer d'onglet n'augmente pas le nombre d'appels OpenAI.




<!-- SOURCE: docs/prd/30_feature/ui_v2/09_DIAGNOSTICS_PARAMETRES.md -->

# 09 — Diagnostics, surveillance, alertes et paramètres

## Objectifs

Avoir une interface fiable quand l'application tourne longtemps : chaque dépendance externe, source de données et calcul significatif expose une **santé vérifiable**. Tous les réglages utilisateur sont accessibles depuis l'UI avec validation, persistance et sécurité.

## A. Santé et diagnostics

Sous-onglets `Santé des services`, `Flux / quotas`, `Incidents`, `Journaux`.

### Table de diagnostic suggérée

| Service | États à distinguer | Signal de santé probant | Action sans risque |
|---|---|---|---|
| IG REST | connecté / token expiré / erreur / hors ligne | probe contrôlé / dernière réussite / latence / code | Tester en lecture seule |
| IG Streaming | connecté / souscrit / droit refusé / stale | transport + abonnement + âge last tick par EPIC | Resouscrire selon quotas |
| Bougies / OHLC | ready / warmup / gap / fallback | nombre, timeframe, source, continuité, âge | Détail série |
| Scanner | prêt / incomplet / erreur / paused | durée dernière passe, marchés scannés, raisons | Relancer manuellement |
| OpenAI | configurée / dernière requête OK / coût / quota / erreur | dernier appel réel, modèle, durée, expiration | Probe explicite seulement |
| RSS / calendrier | OK / exp expiré / indispo | source, collecte, droits | Rafraîchir contrôlé |
| SQLite / Paper | ready / dirty / sauvegarde requise / erreur | version schéma, transaction, checkpoints | Sauvegarder / restaurer après confirmation |
| Workers Qt | prêt / en cours / bloqué / erreur | job, âge, taille file et erreur | Diagnostiquer |

Un simple « CONNECTÉ » doit toujours être interprétable. Le bandeau supérieur n'affiche qu'un résumé et ouvre ce panneau détaillé par clic.

### Politique de health checks

- IG REST : heartbeat **espacé**, non bloquant, conforme quotas et état de session; renouvellement de jetons piloté par adaptateur; backoff exponentiel borné et jitter sur erreurs persistantes.
- IG Streaming : événements de connexion et âge des derniers messages, distinction marché fermé et panne; un flux inactif pendant fermeture marché ne signifie pas automatiquement défaillance sans calendrier.
- IA : pas de ping payant automatique ; statut *configuration disponible / dernière requête / expiration* ; contrôle manuel de bout en bout sur demande.
- Journal : code erreur, correlation_id, instant UTC, nom de la source, impact, remédiation, redaction; ne jamais logger mots de passe, clés ou tokens.
- Afficher le dernier succès réel plutôt que l'instant du dernier rafraîchissement d'UI.

## B. Paramètres

Sous-onglets `Connexions`, `Marchés`, `Stratégies`, `Risques`, `IA`, `Notifications`, `Interface`, `Avancé`.

**Connexions** : DEMO/LIVE, profil et compte, keyring, source des cotations; secrets masqués.
**Marchés** : références surveillées, budget streaming, famille/EPIC bindings contrôlés, timeframes.
**Stratégies** : indicateurs, paramètres, pondérations et seuils; avertir si profil preview non qualifié pour AUTO.
**Risque** : 1 % par trade / 3 % journalier proposés, plafonds positions par marché/global et corrélation, break-even +1R paramétrable, mode exécution et kill switch existant; droits persistants sans activation réelle implicite.
**IA** : provider, modèle, périmètre, consentement, fréquence, TTL, budget, désactivation, envoi des données historiques.
**Notifications** : canaux, gravité, cooldown, test sans trade.
**Interface** : langue FR/EN, thème sombre, taille police, mode compact, format numérique, timezone d'affichage, variation forte on/off/seuils, layout, restaurer défaut.
**Avancé** : diagnostics, export expurgé, réglages versionnés et migration.

Les réglages héritent de la configuration existante. `ConfigMigrator` doit accepter l'ancien `WorkspaceState` largeur/hauteur/splitter et y ajouter optionnellement `layout_version`, `window_geometry`, `main_page`, `tabs`, `panel_visibility`, `locale`, `theme`, sans casser les fichiers existants. Les secrets restent en keyring.

## Exigences

- **GUI2-OPS-001** : états santé IG REST/streaming/market data/IA séparés, vérifiés et horodatés.
- **GUI2-OPS-002** : supervision non bloquante avec backoff, respect quota et distinction marché fermé/flux stale.
- **GUI2-OPS-003** : aucun ping IA payant sans consentement ni action explicite.
- **GUI2-OPS-004** : navigation vers diagnostic détaillé depuis le badge bandeau.
- **GUI2-OPS-005** : configuration de l'interface et langue persistantes; autres paramètres présents mais pas nouveaux droits d'exécution.
- **GUI2-OPS-006** : validation de type, bornes, unités et dépendances des paramètres métier.
- **GUI2-OPS-007** : alertes critiques persistantes et accusé de réception; export journal expurgé.
- **GUI2-OPS-008** : restauration de disposition et migration config backward-compatible.
- **GUI2-OPS-009** : arrêt d'urgence visible uniquement si fonctionnalité effective, sans induire de protection broker non existante.
- **GUI2-OPS-010** : mesures CPU/Qt loops/temps de rendu et erreurs, sans télémétrie externe par défaut.

## Acceptation

Simuler refus de flux IG : badge reste `IG REST connecté` si REST valide mais `Streaming REFUSÉ` et marché `UNAVAILABLE`; aucune erreur masquée. Une clé OpenAI non configurée n'entraîne aucun appel. Changer le thème ou la langue ne modifie pas les montants `Decimal` ni les limites de risque.




<!-- SOURCE: docs/prd/30_feature/ui_v2/10_I18N_FR_EN.md -->

# 10 — Internationalisation FR / EN sous PyQt5

## Décision

**FR + EN font partie de la GUI V2**, et non d'une V3 éventuelle. PyQt5 offre nativement l'internationalisation (`QTranslator`, `QLocale`, fichiers `.ts` / `.qm`). L'effort principal est de sortir les textes actuellement codés en dur des widgets et de prévoir un **retranslate** fiable lors d'un changement de langue.

## Architecture recommandée

- Catalogue des messages `i18n/tradingig_fr.ts`, `i18n/tradingig_en.ts`; fichiers `.qm` compilés et embarqués au packaging; `lupdate`/`lrelease` si disponibles ou outil Qt équivalent identifié par Codex lors du setup.
- Source de référence : **identifiants de messages stables** (`nav.dashboard`, `status.stale`, `position.stop`, `risk.daily_limit`, `scanner.no_trade`) regroupés par contextes, ou usage canonique de `QCoreApplication.translate`/`self.tr`; ne pas mélanger sans convention. Choisir une stratégie unique après spike I18N-0.
- `LanguageManager` unique contrôlant le `QTranslator` installé dans `QApplication`; signal `languageChanged(locale)`, et chaque page implémente `retranslateUi()` pour textes, placeholders, menus, tooltips, headers de tableaux, noms des axes, labels des graphiques et messages métier.
- `ui.locale = fr_FR | en_US` persistant, valeur `fr_FR` par défaut; changement immédiat préféré. Si un widget tiers ne peut pas réétiqueter ses éléments, reconstruire **uniquement la vue** à partir de son view model sans perturber les souscriptions, l'historique ou une position.
- Les `reason_codes` techniques et IDs restent **invariants** (`NO_TRADE`, `DATA_GAP`, `EPIC_NOT_BOUND`, etc.) ; traduire seulement leur affichage par un mapping.
- Les textes IA ou les titres des news sont des données externes : la langue des libellés UI est garantie, la traduction du contenu externe est optionnelle, séparée et potentiellement payante.
- Dates/heures et chiffres via `QLocale` pour affichage ; **le domaine travaille en UTC ISO 8601 et `Decimal`**, sans transformer une virgule décimale localisée en point flottant de domaine.

## Exemple de libellés (catalogue minimal)

| ID stable | Français | English |
|---|---|---|
| `nav.dashboard` | Tableau de bord | Dashboard |
| `nav.scanner` | Marchés / Scanner | Markets / Scanner |
| `nav.watchlist` | Valeurs suivies | Watchlist |
| `nav.positions` | Positions et ordres | Positions & Orders |
| `nav.history` | Historique / Analyses | History / Analytics |
| `nav.macro` | Macro / IA | Macro / AI |
| `nav.diagnostics` | Diagnostics | Diagnostics |
| `nav.settings` | Paramètres | Settings |
| `status.live_data` | Cotations LIVE | LIVE market data |
| `status.paper_execution` | Exécution PAPER | PAPER execution |
| `status.data_gap` | Données interrompues | Data gap |
| `scanner.no_trade` | Aucune opération recommandée | No trade recommended |
| `scanner.not_applicable` | Non applicable | Not applicable |
| `risk.unconfirmed_stop` | Stop non confirmé | Unconfirmed stop |
| `dashboard.realized_pnl` | PnL réalisé | Realized P&L |
| `dashboard.equity` | Valeur du compte (equity) | Account equity |
| `ai.advisory_only` | Analyse IA consultative | Advisory AI analysis only |
| `action.prepare_paper` | Préparer un ticket Paper | Prepare Paper ticket |

## Nombre, monnaie et temps

- FR : `9 935,71 €`; EN : `€9,935.71` si devise EUR et convention EN choisie, sinon symbole explicite + code ISO si ambigu. Format visuel ne modifie pas les contrats.
- Heure affichée `Europe/Zurich` ou zone sélectionnée; horodatages UTC stockés; en-tête « Mis à jour à 10:22 » localisé.
- Changements à chaud de langue/zone ne modifient ni les timestamps bruts, ni les calculs économiques, ni les paramètres.
- Les requêtes IG/OpenAI utilisent une sérialisation numérique protocolaire stable, indépendante de la locale.

## Exigences

- **GUI2-I18N-001** : bascule FR/EN accessible via Interface et persistante.
- **GUI2-I18N-002** : shell, menus, dialogues, tableaux, tooltips, notifications et axes des charts traduits.
- **GUI2-I18N-003** : `retranslateUi()` de tous les composants et tests de changement de langue en cours de session.
- **GUI2-I18N-004** : locales numériques et dates sans corruption de `Decimal`, timezone ou prix/ordres.
- **GUI2-I18N-005** : codes métiers, schémas SQLite et payload API non traduits.
- **GUI2-I18N-006** : fallback stable `en_US`/`fr_FR` avec avertissement développeur pour clé manquante, pas de texte brut visible du type `nav.dashboard`.
- **GUI2-I18N-007** : l'anglais couvre aussi l'interface de diagnostic et les erreurs critiques; aucun bouton d'ordre ambigu.

## Acceptation

Ouvrir une session Paper, changer FR→EN→FR, vérifier même compte, mêmes montants, même sélection, mêmes callbacks et pas de nouvelle requête réseau. Vérifier `1 234,56`/`1,234.56` sans changements des valeurs internes de trading.




<!-- SOURCE: docs/prd/30_feature/ui_v2/11_CONTRATS_ETATS_DONNEES.md -->

# 11 — Modèles de projection et contrats de données GUI

## Doctrine

Les pages reçoivent des **snapshots typés, immuables et datés** des services existants. Elles n'invoquent pas directement IG, OpenAI, SQLite ou le RiskEngine. Les appels opérationnels passent par des **commandes applicatives** contrôlées. `view-model` ≠ source de vérité. Aucune boucle Qt ne doit effectuer un appel HTTP bloquant.

## A. Contrat de lecture (exemple Python, sans migration de langage)

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

class Availability(StrEnum):
    READY = "ready"
    WARMING_UP = "warming_up"
    STALE = "stale"
    DATA_GAP = "data_gap"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"

@dataclass(frozen=True)
class DataProvenance:
    source: str
    observed_at_utc: datetime | None
    received_at_utc: datetime | None
    scope: str
    availability: Availability
    reason_codes: tuple[str, ...] = ()

@dataclass(frozen=True)
class Amount:
    value: Decimal | None
    currency: str
    provenance: DataProvenance
    estimate: bool = False

@dataclass(frozen=True)
class AccountHeaderVM:
    account_id: str | None
    ig_environment: str | None
    product_account_type: str | None
    execution_mode: str
    equity: Amount | None
    available_funds: Amount | None
    day_pnl: Amount | None
    week_pnl: Amount | None
    month_pnl: Amount | None
    open_positions_count: int | None
    ig_rest_status: str
    ig_stream_status: str
    ai_status: str
    generated_at_utc: datetime
```

Ces classes sont **exemples de contrats cible** : Codex doit confirmer les modèles du dépôt, réutiliser le domaine existant et implémenter les conversions dans des services de projection. Ne pas introduire un second modèle autonome de compte si `domain.instruments.Account` et `domain.adapter_contracts.AccountRef` suffisent.

## B. Autres modèles cibles

`MarketRowVM`: `underlying_id`, display name, last_quote, variation, per-component score + band/reasons, AI scope/status, upcoming_event, risk, decision, last_scanned_at, availability.  
`ProductRowVM`: `product_epic`, `bound_underlying_id?`, product type, exposure direction, order capability, bid/ask, spread, fees/KO/expiry/size/currency, provenance.  
`PositionRowVM`: account+environment+position ID (clé composite), Paper/Broker, price/age, PnL and status, stop proposed/confirmed, KO, TP, state, permissions/capabilities, audit link.  
`PnlSeriesVM`: account scope, Paper/Broker, granularity (DAY/WEEK/MONTH/YEAR), currency, per-bucket pnl realized/net/estimated, opening equity, ending equity, missing flags, methodology label, provenance.  
`MarketAnalysisVM`: `underlying_id`, technical/timeframe readiness, strategy outputs, macro snapshot, AI snapshot with `model_id`, `prompt_version`, `valid_until`, validated bindings and confidence; source-specific unknowns.  
`HealthServiceVM`: service, status, last_success_at, last_error_at, latency, quota, age, reason and available probe.  
`OptimizationProposalVM`: proposal ID, scope, old/new params, hypothesis, dataset fingerprint, replay evidence, confidence/limits, approval state, created_at, version.

## C. Calculs / garanties des projections

- Clés stables par `(environment, account_id, product_epic, position_id)` ; ne jamais mélanger DEMO/LIVE ou Paper/IG.
- `DataProvenance` source+UTC+quality; `unknown` n'est jamais converti en `0` pour score/solde/PnL.
- Les données expirées gardent leur date d'origine, avec `STALE` et requêtes interrompues selon contrat.
- Un calcul de PnL dans la GUI est interdit : employer `AnalyticsProjectionService` et la logique d'événements/FX validée.
- Les derniers prix de produits différents et les historiques de référence ne sont **pas** interchangeables.
- `Error` et `Loading` sont des états en première classe, pas du texte générique sans cause.

## D. Bus de snapshots / commandes

```text
IG REST / Lightstreamer ─┐
PaperSession / SQLite ────┼──> Application services / cache cohérent
Scanner / Macro / OpenAI ─┘               │
                                         v
                               UI read models / projections
                                         │
                          Qt signal (queued, coalesced)
                                         │
                                         v
                         Page controllers / QAbstractTableModels
                                         │
                      Intentions explicites utilisateur
                                         v
                       Application command facade
                              │             │
                       RiskEngine     Permissions / capabilities
                              │             │
                              └──────┬──────┘
                                     v
                              Paper ONLY (GUI V2)
```

L'illustration n'introduit aucun chemin d'exécution broker LIVE. Un `OpenAIHealthModel` n'est **pas** une session connectée permanente.

## E. Performance / cycle de vie

- Une seule source d'abonnement streaming pour l'application, par combinaison environnement/compte/EPIC, avec références/release propres.
- Diffusion UI bornée (p.ex. 2-4 Hz pour lignes de cotation, 1 Hz bandeau PnL, mise à jour graphique coalescée), sans ralentir les calculs métier ou perdre la date de la dernière observation.
- Workers/threads via signaux Qt `QueuedConnection`, annulation et générations de requêtes; les résultats d'une ancienne session de compte ne doivent jamais repeupler la nouvelle.
- Verrouillage limité aux états partagés ; les modèles `QAbstractTableModel` ne se modifient que dans le thread GUI; le core reste testable hors Qt.
- Pas de persistance de secrets ni de payload brut non expurgé dans les tableaux ou les exports.

## Exigences

- **GUI2-DATA-001** : snapshots GUI immuables, provenance, timestamp, scope et status.
- **GUI2-DATA-002** : projections financières centralisées et unités/devise sûres.
- **GUI2-DATA-003** : un seul runtime/connecteur/flux, pas d'appels cachés en UI.
- **GUI2-DATA-004** : états inconnus, périmés, non applicables, données manquantes conservés jusqu'à l'UI.
- **GUI2-DATA-005** : émission Qt thread-safe, coalescing et sélection par IDs stables.
- **GUI2-DATA-006** : séparation analyses/consultation des commandes transactionnelles.
- **GUI2-DATA-007** : migration backward-compatible des états/config, absence de perte de journal.




<!-- SOURCE: docs/prd/10_architecture/gui_v2_refactor.md -->

# Architecture — Refonte GUI V2 par migration incrémentale

**Cible :** Windows / PyQt5 / PyQtGraph / Python 3.12; branche source examinée `chore/sr41-upgrade`, commit `1844916` du 09/11/2026. **Code non modifié par ce PRD.**

## 1. Diagnostic du code de référence (faits vérifiés)

| Emplacement actuel | Observation | Conséquence pour GUI V2 |
|---|---|---|
| `ui/main_window.py` | 3 558 lignes, coordonne IG, flux, scanner, macro, IA, Paper, persistance et layout; `QSplitter` + `QTabWidget`, pas de `QDockWidget` | Extraire l'orchestration et découper les pages; pas de réécriture en une seule PR |
| `ui/chart_view.py` | Chart PyQtGraph en production | **Réutiliser** la vue graphique et ses modèles; ne pas réimplémenter chandeliers/ranges |
| `ui/product_selector.py`, `ticket_view.py`, `paper_portfolio_view.py` | Widgets métier existants | Les encapsuler d'abord dans des pages; remplacer progressivement les tables si nécessaire |
| `ui/scanner_view.py` | `QTableWidget` et calcul de rendu | Passage gradué à `QTableView` + model/proxy pour streaming et catalogue |
| `services/scanner_runtime_batch_service.py` | assemble batch depuis bindings exacts et bougies de session, déclenchement GUI principalement manuel | Découpler scheduling/présentation et afficher chaque marché même incomplet |
| `services/indicator_service.py`, `technical_strategy_service.py`, `scanner_component_service.py` | indicateurs, stratégies, scores déterministes | Rester source de vérité; aucun score redéfini dans des widgets |
| `services/analytics_service.py` | agrégation PnL réalisé jour/semaine/mois/année et par devise | Ajouter projections equity/stats avec provenance; pas de courbe historique sans données |
| `services/paper_session.py`, `paper_broker.py` | exécution locale, save/restore explicitement demandés | Reprendre à l'identique; pas de restaurations automatiques non approuvées |
| `adapters/ig_rest.py` | méthodes générales d'ouverture/modification/clôture IG lèvent `LiveTradingDisabledError` | Les nouveaux boutons d'exécution réels restent interdits |
| `app/config.py::WorkspaceState` | fenêtre largeur/hauteur et taille du splitter | Étendre par migration versionnée avec onglets, géométrie, thème, locale |
| `docs/codex/SR_PACK_VERSION.json` | SR Method 4.1.0 présent | Couvrir les lots par Scope/Verification/Activation, sans plan TDD obligatoire |

**Ne pas déduire des 606 tests signalés localement par Codex que la nouvelle GUI est déjà validée.** Le commit lu n'a pas été exécuté par cet audit; les validations Windows/connexion réelles restent du travail de Codex et de l'utilisateur.

## 2. Règles de dépendances

```text
trading_ig_assistant/
  domain/          # pure, sans Qt ni HTTP ; NE PAS déplacer sans nécessité
  adapters/        # IG REST/Streaming, OpenAI, RSS, calendrier ; conserver
  persistence/     # SQLite, journal, session Paper ; conserver contrats
  services/        # métier existant : indicateurs, scanner, risque, Paper
  app/
    runtime/                 # propriétaire unique du cycle de vie, composants existants injectés
    ui_facade.py             # API de consultation et commandes permises
    projections/             # nouveaux DTO UI construits depuis domain/services
      account_projection.py
      pnl_projection.py
      market_projection.py
      position_projection.py
      health_projection.py
      optimization_projection.py
  ui/
    shell/
      main_window_v2.py     # QMainWindow : composition et navigation seulement
      nav_sidebar.py
      account_header.py
      macro_compact_bar.py
      page_router.py
    pages/
      dashboard_page.py
      scanner_page.py
      watchlist_page.py
      positions_page.py
      analytics_page.py
      macro_ai_page.py
      diagnostics_page.py
      settings_page.py
    models/
      market_table_model.py
      product_table_model.py
      position_table_model.py
      trades_table_model.py
      pnl_series_model.py
    widgets/
      kpi_card.py
      freshness_badge.py
      score_chip.py
      financial_charts.py
      ...                   # wrappers des widgets PyQtGraph et Paper existants
    theme/
      tokens.py
      theme_manager.py
      tradingig_dark.qss
    i18n/
      language_manager.py
      tradingig_fr.ts
      tradingig_en.ts
```

Arborescence **proposée** : conserver les chemins actuels tant qu'un lot n'a pas prouvé qu'il peut migrer les imports et les tests. Ne pas créer des fichiers d'adaptation vides juste pour correspondre au diagramme. Aucun nouveau framework GUI et pas de serveur web.
## 3. `TradingRuntime` et la façade

- `TradingRuntime` (ou application controller équivalent) possède la session IG, les listeners, les timers/schedulers et les services Paper existants. Il crée **une seule** instance de `IGRestAdapter`, `IGStreamingAdapter` par contexte selon l'architecture existante; la navigation de page ne crée ni client ni souscription supplémentaire.
- `UIFacade` expose `get_account_header()`, `subscribe_market_rows()`, `get_positions(scope)`, `get_pnl_series(scope, period)`, `get_macro_events()`, `get_market_analysis(underlying_id)`, `get_health()` sous formes typées, sans PyQt dans le domaine.
- Commands distinctes : `refresh_scanner`, `request_ai_analysis`, `prepare_paper_ticket`, `apply_paper_stop_tightening`, `save_paper_snapshot`, `switch_account`; chaque commande valide scope/capabilities et journalise les conséquences. Le simple rendu d'une page n'appelle jamais une commande.
- Le GUI reçoit des snapshots **immuables avec `generation_id`**; après changement de compte une réponse d'une ancienne génération est ignorée (évitant l'affichage cross-account). Le `QThread` et ses signaux restent côté façade Qt/application bridge.
- Eviter un store qui réplique tout le domaine : une projection de lecture légère suffit si les services existants sont fiables; conserver un seul propriétaire de l'état métier.

## 4. Refactorisation de `MainWindow` sans « big bang »

1. **Geler le comportement** : vérifier la branche propre, les tests unitaires/régression et créer une branche spécifique. Tracer la carte réelle des callbacks/signaux de `main_window.py` et les invariants (IG connect/disconnect, compte, produit, flux, scanner, OpenAI, Paper, persistence).
2. **Introduire le shell V2 hors circuit** (`MainWindowV2`) avec des pages remplaçables et fausses données étiquetées DEMO UI uniquement dans les tests; aucune commande réseau ni ordre.
3. **Brancher header et navigation** sur projections réelles readonly; l'ancienne fenêtre reste accessible par un flag temporaire `--ui legacy|v2` ou configuration dev équivalente sans lancer deux runtimes simultanément.
4. **Extraire un bloc à la fois** : account/profiles, scanner, macro/IA, Paper, sans déplacer les calculs métier et sans changer le format des événements. Ajouter des tests de parité des snapshots avant de supprimer les anciens callbacks.
5. **Migrer les tableaux** nécessitant de fortes mises à jour de `QTableWidget` vers `QAbstractTableModel`, avec `Qt.DisplayRole`, `Qt.ForegroundRole`, `Qt.BackgroundRole`, `Qt.ToolTipRole`, `Qt.UserRole` pour identifiants, `QSortFilterProxyModel`; préserver l'index sélectionné via identifiants.
6. **Reprendre `ChartView` existant** dans la nouvelle Watchlist; préserver les méthodes et événements. Ajouter sous-plots RSI/MACD/ATR uniquement si la structure existante permet un ajout compatible; éviter rebase/remplacement du graphique.
7. **Extraire progressivement les coordinations UI** et retirer l'ancien chemin après parité/validation Windows. Objectif indicatif : `MainWindowV2` devient un assembleur de pages plutôt qu'un module de plusieurs milliers de lignes; la taille en lignes n'est pas un critère isolé de DoD.

**Règle absolue** : aucun refactor d'UI n'est une justification pour activer les méthodes d'ordre dans `IGRestAdapter`. L'application doit rester PAPER/ANALYSIS côté GUI V2.

## 5. Performance / threads

- Les données IG arrivent par listeners/threads existants; tous les `QAbstractTableModel` se mettent à jour **uniquement dans le thread Qt GUI** via événements `QueuedConnection` ou équivalent.
- Grouper les updates (tick coalescing), mettre à jour lignes/cellules changées (`dataChanged`) et non un `resetModel()` complet à chaque prix. Rechercher les goulots si 500+ produits affichés.
- Les requêtes REST, OpenAI, RSS, scraping interdit, accès DB important et validation longue s'exécutent hors GUI thread ; annulation/résultats de génération obsolète maîtrisés.
- Paramètres de fréquence UI (proposés) : header 1 Hz, tables de prix 2-4 Hz, chart 1-4 Hz, analyse technique aux **bougies clôturées**, macro selon TTL autorisé, pas de rafraîchissement des événements sans source.
- Pas d'appels OpenAI de « heartbeat » ; statut IA dérivé de la configuration et des derniers probes réellement consentis.

## 6. Données / sauvegarde / migrations

- Étendre `WorkspaceState` sans casser les JSON existants : version `layout_version=2`, `window_geometry`, `active_page`, `active_subtabs`, `sidebar_collapsed`, `theme`, `locale`, visibility, table column state et éventuel `dock_state` en encodage sûr et contrôlé.
- Garder la migration **idempotente et réversible** ; si des schémas SQLite supplémentaires sont nécessaires pour equity snapshots ou journal d'optimisation, migration testée from-scratch et from-existing, avec sauvegarde et rollback. Aucune migration automatique du journal sans vérification.
- Les snapshots Paper actuels avec checksum et la restauration explicite ne changent pas; une GUI à onglets n'est pas une nouvelle politique de récupération.
- Les **images du PRD** servent de guide esthétique. Des prix/scores/impressions de disponibilité trompeurs dans les mocks ne doivent pas être copiés dans des données réelles.

## 7. Internationalisation de l'architecture

Préparer l'i18n **au lot GUI de fondation** : `LanguageManager`, locale persistée, chaînes de navigation/toolbar dès le premier widget; ne pas ajouter d'abord 50 écrans en français codé dur pour « traduire à la fin ». Les codes métiers restent invariants et les conversions `QLocale` n'affectent pas les calculs numériques.

## 8. Comportements à ne surtout pas modifier sans lot séparé

- Politique OHLC `session-only` : pas de REST-backfill ni réutilisation automatique des caches au démarrage tant que l'utilisateur ne l'a pas validé.
- Flux IG soumis aux droits et quotas par compte / EPIC ; ne pas souscrire tous les 567 produits présents dans le catalogue.
- Binding dérivé EPIC→underlying strict, pas de rapprochement par nom.
- Revue Paper explicite / sécurité des stops / no widen / session save-restore.
- LIVE trades & AUTO désactivés et `LiveTradingDisabledError` conservé.
- Traitement IA consultatif, sources et TTL; pas de déclenchement automatique d'ordres ou de recherche web coûteuse.

## 9. Exigences structurelles

- **GUI2-ARCH-001** : code métier indépendant de PyQt / sources transport; aucune règle de risque dans l'UI.
- **GUI2-ARCH-002** : une seule session et un seul runtime central, sans multiplicateurs d'appels réseau après navigation.
- **GUI2-ARCH-003** : projections typées et identifiées par compte/market/product/mode.
- **GUI2-ARCH-004** : migration incrémentale avec ancien écran en secours jusqu'à validation.
- **GUI2-ARCH-005** : parité du fonctionnel existant démontrée par tests, et non supposée après découpage.
- **GUI2-ARCH-006** : un nouvel onglet ne peut appeler directement ni adapter IG ni keyring ni commande de trading.
- **GUI2-ARCH-007** : découpage Qt threads, coalescing et flux stales correctement gérés.
- **GUI2-ARCH-008** : configuration et persistance rétrocompatibles, sans perte de Paper ou journal.
- **GUI2-ARCH-009** : thème/i18n centralisés et testables séparément des vues métiers.
- **GUI2-ARCH-010** : niveau d'effort et risques du refactor motivés par résultats, pas des déplacements cosmétiques massifs.

## 10. Exemple de frontière de façade (indicatif)

```python
from typing import Protocol
from collections.abc import Callable

class TradingUIFacade(Protocol):
    def read_account_header(self): ...
    def read_dashboard(self, scope, period): ...
    def read_market_rows(self, watchlist_id): ...
    def read_position_rows(self, scope): ...
    def read_health(self): ...
    def request_refresh(self, section: str) -> None: ...
    def subscribe(self, kind: str, on_snapshot: Callable) -> object: ...

# Never add:  def place_live_order_from_button(self, ...): ...
```

Dans le code effectif, remplacer `...` par des types réutilisant les classes `domain`; garder la façade distincte de la classe `QMainWindow`. Les commandes Paper utilisent le service existant et les gates explicites.




<!-- SOURCE: docs/prd/02_tasks/phases/R09_gui_v2.md -->

# R09 — GUI V2 : migration incrémentale et i18n FR/EN

**Statut :** proposé, à découper par Codex selon SR Method 4.1 après audit source.  
**Périmètre :** GUI, vues de lecture, commandes Paper existantes, thème, traduction, projections et QA.  
**Interdits :** activation de trading LIVE/AUTO, extension non autorisée de l'API IG, appel IA sans consentement, modification silencieuse de stratégie/risque.

## Dépendances et fondations

R00–R07 et les services R08 existants dans le dépôt sont des sources à **auditer**, pas à refaire. Vérifier commit, état Git, 606 tests locaux reportés vs résultat de la machine actuelle, configuration JSON et données Paper. Appliquer le contrat de compétence SR 4.1 : Scope → Verification (Activation seulement si lancement/build/déploiement demandé). Une tâche simple n'appelle pas artificiellement tous les documents SR.

## Lots proposés

| Lot | Priorité | Livrable observable | Préconditions | Ne doit pas changer |
|---|---|---|---|---|
| `R09-00` | P0 | Baseline Git, inventaire MainWindow, mapping signaux/services, captures actuelles, tests | Branche cible propre | Aucun code métier |
| `R09-01` | P0 | Design tokens, QSS, `LanguageManager`, base FR/EN, test DPI | R09-00 | Ordres / API |
| `R09-02` | P0 | `MainWindowV2` shell, sidebar, header, pages factices **explicitement démo UI** | R09-01 | Services ni state broker |
| `R09-03` | P0 | Facade + typed snapshots account/health, interaction compte, données de démo réelles readonly | R09-02 | Autorisations d'ordres |
| `R09-04` | P1 | Dashboard données attestées, séries synchronisées PnL/equity (ou N/A), statuts et positions | R09-03 | Analytics historique sans preuve |
| `R09-05` | P1 | Scanner multi-marchés / catalogue IG, QAbstractTableModel, filtres, statuts et binding | R09-03 | Scanner weights / score logic |
| `R09-06` | P1 | Watchlist + ChartView existant, indicateurs + IA + LONG/SHORT/NO_TRADE | R09-05 | Moteurs de stratégies |
| `R09-07` | P1 | Positions/Ordres/Paper unifiés, save/restore et confirmation conservées | R09-03 | RiskEngine, stop rules, IG order gates |
| `R09-08` | P1 | Historique, analytics, macro/calendrier, diagnostics et alertes | R09-04/07 | Providers/licences IA |
| `R09-09` | P1 | Workflow d'analyse IA des résultats **consultatif**, propositions et tests hors ligne | R09-08 | Aucun paramètre live auto-modifié |
| `R09-10` | P0 à clôture | QA FR/EN, DPI, streaming, long-run, migration config, performance, preuve de non-régression | Tous | Aucun déploiement live |

Les lots doivent rester **petits, testables, séquencés**. Une page peut être intégrée avant ses sources avancées à condition que l'état `N/A` soit fidèle. Pas d'interdiction de corriger un bug nécessaire aux lots, mais il doit être isolé, tracé et testé.

## Jalons d'acceptation

**M1** : style/nav/header/i18n sur Windows, même runtime et données métier.  
**M2** : scanner et graphique opérationnels avec statuts de fraîcheur fiables; 500+ lignes catalogue sans gel.  
**M3** : positions Paper et historique sous nouvelle GUI, compte/live séparés et protection préservée.  
**M4** : dashboard honnête avec PnL réel disponible, equity affichée seulement si prouvée, recommandations IA gouvernées.  
**M5** : validation visuelle complète, profils sauvegardés et compatibilité du projet; éventuellement retirer `legacy` après approbation.

## Preuves exigées à chaque lot

- Diff de code limité aux fichiers touchés et consommateurs, intégration sans imports circulaires.
- `pytest -q` (tests ciblés puis ensemble sur plateforme de développement si possible) et `ruff check src tests`.
- Tests `pytest-qt` si présent; sinon smoke native `QApplication` offscreen pour la logique + capture manuelle réelle Windows (l'offscreen n'est pas une preuve de rendu final Windows).
- Tests de faux adaptateurs/quotes/positions et refus de droits; aucune requête réelle exigée par tests GUI.
- Captures Windows 1920×1080, 1366×768, DPI 125 %, FR et EN pour pages modifiées; log des champs non vérifiés.
- Aucun appel à IG AUTO/LIVE et aucun coût IA sans consentement sur la nouvelle navigation.

## Condition avant ajout de trading automatique

Cette phase **n'accorde aucune** activation d'ordres LIVE/AUTO. Une fois GUI V2 validée, reprendre les plans quantitatifs R08 sur datasets versionnés, capacités IG et procédures distinctes de validation humaine.




<!-- SOURCE: docs/prd/05_coding_agent/gui_v2_codex_guide.md -->

# Codex — Guide d'implémentation GUI V2 sous SR Method 4.1

## Contexte et autorités

- Référentiel produit canonique : `docs/prd/PRD.md`, F001–F013, documents architecture, `docs/CURRENT_STATE.md` **à interpréter selon dates**.
- Addendum GUI : `docs/prd/30_feature/ui_v2/00_INDEX_GUI_V2.md` et documents liés.
- Version contrôlée au moment de la rédaction : `chore/sr41-upgrade` commit `1844916`; vérifier la HEAD actuelle avant modification.
- Priorité des preuves : code réel, tests et validation Windows datés > notes anciennes et maquettes fictives.
- SR 4.1 : `AGENTS.md`, `docs/codex/SR_BOOTSTRAP.md`, `docs/codex/SR_ROUTES.json`, et skill de diagnostic/architecture/UI si son trigger est exact; pas de chargement massif et non nécessaire.

## Premier tour demandé à Codex — sans modifier le code

1. Confirmer `git status`, `git branch --show-current`, `git log -1`, version SR et résultats tests actuels.
2. Lire uniquement les sources utiles : `ui/main_window.py`, `ui/chart_view.py`, `ui/product_selector.py`, `ui/scanner_view.py`, `ui/paper_portfolio_view.py`, `app/config.py`, `services/analytics_service.py`, interfaces `domain`, `tests/unit/test_ui_shell.py`.
3. Documenter les **propriétaires** des sessions, quotes, Paper et workflows IA, chemins de callbacks, invariants et points de blocage.
4. Proposer le découpage `R09-00` à `R09-10`, les fichiers réellement touchés, dépendances, effets hors lot, risques et stratégie de migration sous forme compacte.
5. Présenter le plan et attendre validation avant migrations non-locales / changements d'architecture risqués. Si autorisé, faire **une PR ou commit par lot**, sans mélange unrelated.

## Architecture cible — règles normatives

- Les pages Qt affichent et émettent des intentions ; elles n'appellent pas directement IG, OpenAI, SQLite, ou RiskEngine.
- Services métier existants = sources de vérité; `UIFacade`/application controller transforme en projections datées et expose commandes contrôlées.
- Réutiliser l'instance existante `ChartView`, modules scanner, Paper et macro; pas de réécriture pour changer l'aspect.
- `QMainWindow` shell, `QStackedWidget` pages, `QTabWidget` sections, `QDockWidget` seulement mode expert; model/view pour table de forte volumétrie.
- Ne pas créer un flux ou une connexion par page ; une seule propriété par runtime et scope.
- Les tables reçoivent des DTO immuables avec provenance, UTC, `READY/STALE/WARMING_UP/N/A`, et clés stables.
- `QTranslator` + FR/EN installés dès le shell; `Decimal`/dates jamais soumis à une conversion métier localisée.
- `IGRestAdapter.create_otc_position/update_position/close_position/create_working_order` restent désactivés selon code existant; ne pas dupliquer un autre chemin pour passer outre.

## Workflow par lot

**Scope Gate** : objectif, autorité, fichiers, consommateurs, état protégé et plus petite modification suffisante.  
**Implémentation** : changement chirurgical, sans refactor hors périmètre ; préserver compatibilité configs et journal.  
**Verification Gate** : tests ciblés puis ensemble/ruff, screenshot native Windows si vue, preuve de non-régression du comportement Paper/IG/IA.  
**Activation Gate** : uniquement si l'utilisateur demande explicitement une activation/build/restart/déploiement ; ne signifie jamais autorisation de trading LIVE/AUTO.

Ne pas imposer la méthode TDD comme gate SR 4.1, ne pas inventer des échecs, ne pas déclarer « done » si les captures DPI ou scénarios Paper restent à tester humainement. Conserver états `blocked`/`user_testing` plutôt que des conclusions sans preuve.

## Ordre recommandé des refactors

1. Shell/Theme/LanguageManager.
2. `AppViewFacade` à partir des services existants; test en fake adapter.
3. Migration du bandeau compte/ribbon avec données attestées.
4. `MarketTableModel`, `PositionTableModel`, `PnlSeriesProjection`.
5. Recomposition Watchlist avec ChartView.
6. Recomposition ticket et portefeuille Paper; confirmation identique.
7. Historique + analytics + optimisations IA consultatives.
8. Diagnostics et paramétrage complet; nettoyage progressif de l'ancienne fenêtre.

## Critère d'arrêt / rejet

Stopper en cas de : conflit non analysé sur une sauvegarde Paper; modification de schéma sans migration testable; risque de mauvais compte; duplication des souscriptions; activation d'ordre réel; résultats de prix sans provenance; changements sur des fonctions broker non autorisées; coût IA imprévu; test de GUI dégradé sans plan de restauration.

## Livrable de chaque lot Codex

1. Fichiers touchés et justification ;
2. comportement avant/après ;
3. tests exécutés, preuve et résultat ;
4. captures Windows si visuel ;
5. contrats/provenance/risques non validés ;
6. prochain lot SR recommandé.




<!-- SOURCE: docs/prd/90_quality/gui_v2_qa.md -->

# GUI V2 — Qualité, scénarios et critères d'acceptation

## Préambule

La référence visuelle est la série de maquettes V2. **Les maquettes ne sont pas des tests et leurs cotations ne sont pas des fixtures financières**. Chaque test utilise des données synthétiques explicitement marquées ou des sources autorisées, distingue Paper/DEMO/LIVE et ne place aucun ordre réel.

## Matrice d'acceptation

| ID | Vérification | Critère précis | Preuve |
|---|---|---|---|
| AC-GUI2-01 | Shell & navigation | 8 rubriques, tabs internes, header persistent, pas de reconnexion au clic | Windows screencast + mock session counter |
| AC-GUI2-02 | Thème sombre | palette, hiérarchie, contrastes, boutons vrais | captures Windows 1920×1080 et 1366×768 |
| AC-GUI2-03 | DPI | 100/125/150 %, aucun contrôle critique coupé | captures + navigation clavier |
| AC-GUI2-04 | FR / EN | navigation/menu/table/tooltips/erreurs/axes traduits; état inchangé FR→EN→FR | tests Qt + screenshots |
| AC-GUI2-05 | Header comptes | compte, environnement marché, mode Paper/Analysis, fonds/PnL seulement s'ils existent | mocks + changement de compte |
| AC-GUI2-06 | Santé IG | REST OK/stream refusé séparés, âge de quote exact, pas de faux connecté | fake adapter, clock contrôlée |
| AC-GUI2-07 | Santé IA | sans token: not-configured; pas de ping/payeur; dernière analyse expirée | fake OpenAI compteur appels |
| AC-GUI2-08 | Dashboard PnL | jour/semaine/mois/année EUR/%; équité synchronisée; N/A si historique absent | dataset fixtures avec trous |
| AC-GUI2-09 | Comptabilité stats | ordres refusés ≠ trades perdants; gagnants/perdants/nuls séparés | calcul connu, tests déterministes |
| AC-GUI2-10 | Portefeuille | table Paper et IG toujours identifiées, position stale marquée | replay Paper/connexion en lecture seule |
| AC-GUI2-11 | Scanner | multi-marchés, scores séparés, NO_TRADE, UNKNOWN non = 0 | fixtures et snapshot test |
| AC-GUI2-12 | Performance catalogue | 500+ lignes scroll/tri/filtre sans UI freeze | mesure Windows durée update |
| AC-GUI2-13 | Bindings | EPIC non lié ⇒ IA not-applicable et aucune inférence par nom | fixture DEMO barrière CAC |
| AC-GUI2-14 | Watchlist | chart existant + indicateurs sans valeurs sur données warmup | replay candle fragments |
| AC-GUI2-15 | LONG/SHORT | décisions marché séparées d'order_side d'un dérivé | 4 cas CFD/Barrière, sans ordre |
| AC-GUI2-16 | Paper actions | ouverture, save, restart, restore manuel, stop tighten, close | scénario intégration local |
| AC-GUI2-17 | Broker safety | aucun ordre LIVE/AUTO nouveau; méthodes disabled conservées | tests de negative capabilities |
| AC-GUI2-18 | Macro / calendrier | source/heure/TTL et données absentes ⇒ unknown, pas d'événement inventé | fixture sans provider |
| AC-GUI2-19 | IA apprentissage | proposition sans apply, dataset fingerprint, test/review/rollback | scenario offline + UI |
| AC-GUI2-20 | Persistance UI | géométrie, langue, onglet, palette et layout restaurés; JSON historique lu | migrations conf tests |
| AC-GUI2-21 | Timezone/devise | FR et EN formatent sans modifier Decimal ni UTC | tests num + DST |
| AC-GUI2-22 | Qt threading | aucune mise à jour model hors thread UI, aucun HTTP synchrone UI | instrumentation et tests |
| AC-GUI2-23 | Streaming quota | pas d'abonnement multi-produits à chaque navigation | fake IG adapter spy |
| AC-GUI2-24 | Stale/gap | screenshot affiche état réel, prix et horodatage stables pendant panne | fake clock + drop events |
| AC-GUI2-25 | Accessibilité | tab navigation, focus visible, non dépendance à la seule couleur | manual + smoke |
| AC-GUI2-26 | Erreurs / logs | messages lisibles, absence secrets, erreurs persistantes | sanitized export + tests |

## Objectifs mesurables proposés (non garantis)

- Temps de réponse à interaction souris/menu dans le shell : cible p95 < 150 ms sur machine de test Windows, à mesurer en contexte réaliste.
- Rafraîchissement des tables/catalogue : pas de freeze > 250 ms dû au rendu sur jeu mock 500+ produits; les couches réseau sont exclues du benchmark de rendu.
- Temps complet d'ouverture Dashboard avec mock data : cible < 2 s sans lancer de connexion supplémentaire.
- Mémoire, abonnements actifs, timers/workers et taille de file stables après 1 h de bascule entre pages; vérifier un scénario de 4 h de streaming réel autorisé dans une validation ultérieure.
- Pas de crash lors de déconnexion IG, switch compte, redimensionnement, restauration layout corrompu et changement de langue.

Les seuils sont des **objectifs initialement proposés**, à ajuster après la baseline mesurée et les contraintes matériel/flux.

## Stratégie de tests

1. **Unitaires** : projections PnL, dates, score labels, trad/format, mapping DTO, filters/model data roles, permissions, config migration.
2. **Intégration hors ligne** : faux adaptateurs IG/OpenAI, séries fictives bougies, PaperSessionService et SQLite temporaire, sans secrets; compteur de réseau.
3. **GUI offscreen** : création `QApplication`, changement de pages/langue, déclenchement d'intentions, stabilités, pas de demande réseau.
4. **Tests natifs Windows** : captures avant/après aux dimensions annoncées, navigation clavier, DPI, contraste, scroll, stress catalogue. Le validateur navigateur Playwright de SR Method ne prouve pas le rendu d'une app PyQt5 desktop : utiliser un outil/capture natif ou validation visuelle humaine.
5. **DEMO/LIVE readonly** : facultatif sur accès autorisé, compte correct, streaming uniquement des marchés permis; jamais un test d'ordre réel dans la suite GUI.

## DoD de la phase R09

Tout ce qui précède est soit validé par preuve ou explicitement marqué `user_testing`, `blocked` ou `deferred`. Le code de l'ancienne fenêtre n'est supprimé qu'après parité des flux IG, du Paper, du scanner et des workflows IA + validation utilisateur. Aucune nouvelle méthode d'ordre LIVE ou AUTO n'est activée.
