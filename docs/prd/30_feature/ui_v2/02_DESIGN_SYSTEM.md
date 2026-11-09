# 02 — Design System sombre TradingIG

## Référence visuelle (validée sur l'intention)

**Référence visuelle « Dashboard souhaité » :** consulter [le catalogue des maquettes approuvées](../../95_sources/images/ui_v2/REFERENCE_IMAGES.md). Les PNG originaux ne sont pas encore inclus dans cette branche.

**Référence visuelle « Scanner souhaité » :** consulter [le catalogue des maquettes approuvées](../../95_sources/images/ui_v2/REFERENCE_IMAGES.md). Les PNG originaux ne sont pas encore inclus dans cette branche.

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
