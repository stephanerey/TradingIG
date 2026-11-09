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
