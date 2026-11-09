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
