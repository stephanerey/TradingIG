# PROMPT CODEX — TradingIG GUI V2, démarrage de l'analyse et lot R09-00

Tu travailles dans le dépôt local `C:\Projects\TradingIG`. La GUI actuelle est provisoire. L'utilisateur a validé le **style sombre moderne** des images sous `docs/prd/95_sources/images/ui_v2/` et veut une interface **FR/EN**, à base de bandeau de compte fixe, menu latéral, huit pages et sous-onglets.

## Première mission — analyse/plan, pas de grand refactor immédiat

Lis **dans cet ordre et de façon ciblée** :

1. `AGENTS.md`, `docs/codex/SR_BOOTSTRAP.md` et les routes SR 4.1 nécessaires.
2. `docs/prd/PRD.md`, `docs/prd/30_feature/F012_windows_workspace_and_settings.md`, `docs/prd/30_feature/F013_alerts_diagnostics_and_resilience.md`.
3. `docs/prd/30_feature/ui_v2/00_INDEX_GUI_V2.md` puis uniquement les fiches pertinentes pour le premier lot.
4. `docs/prd/10_architecture/gui_v2_refactor.md` et `docs/prd/02_tasks/phases/R09_gui_v2.md`.
5. `docs/prd/05_coding_agent/gui_v2_codex_guide.md` et `docs/prd/90_quality/gui_v2_qa.md`.
6. Le code réel `ui/main_window.py`, les widgets existants, `app/config.py`, les services IG/Scanner/Analytics/Paper et leurs tests — ne pas tout lire aveuglément, faire une cartographie des appels.

Confirme HEAD, branche, git status, état SR, tests disponibles et le cas échéant les écarts depuis le commit de référence `1844916`. Ne prends aucun rapport ancien pour une vérité supérieure au code et aux tests datés.

**Présente-moi ensuite** une proposition de lots SR détaillée de R09-00 à R09-10, avec fichiers à créer/modifier, sources de données réutilisées, interactions entre pages, risques, tests de vérification et screenshots Windows attendus. Commence par le lot **R09-00** puis **R09-01** si leur périmètre est validé. Évite une réécriture de MainWindow : extrais progressivement.

## Contraintes impératives

- Aucun trading réel ou automatique. Conserve `LiveTradingDisabledError` et les protections Paper.
- Ne recharge pas au démarrage des historiques IG/caches de bougies contre la décision actuelle `session-only`.
- Ne souscris pas tous les produits IG au streaming : seuls les marchés autorisés/surveillés et les droits constatés sont utilisables.
- Ne génère pas de données de performance historiques fictives. Affiche `N/A` avec raison quand l'historique n'existe pas.
- Les pages Qt n'appellent pas directement IG/OpenAI/SQLite; elles consomment des DTO/view-models datés issus d'un runtime unique.
- Les analyses IA et propositions d'amélioration de stratégie restent consultatives, sans changement automatique des paramètres.
- Implémente la localisation FR/EN dès le shell par PyQt5 `QTranslator` (ou solution Qt native équivalente justifiée), sans altération des calculs `Decimal` ou timestamps UTC.
- Le style sombre doit suivre les tokens documentés, les maquettes servant de référence d'intention **et non de vérité fonctionnelle**.
- Respecte la méthode SR 4.1 : Scope, Verification, Activation uniquement si explicitement demandée ; petites mutations, preuves exactes, aucun TDD ritualisé.

Le premier livrable est **un plan précis et un inventaire de risques**, pas un démarrage simultané de toutes les pages. Je valide la refactorisation structurante avant de l'appliquer.