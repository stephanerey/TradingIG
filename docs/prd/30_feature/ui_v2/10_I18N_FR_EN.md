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
