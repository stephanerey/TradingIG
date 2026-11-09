# Definition of Done

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-10-22

A change is done only when:
- relevant PRD files are referenced in the PR/commit notes;
- code is typed and structured according to package boundaries;
- unit tests pass;
- external API calls are behind adapters and can be mocked;
- no credentials, tokens, account IDs, or raw auth headers are logged;
- user-facing errors are clear and actionable;
- risk-affecting logic has tests;
- journal/event logging is updated when behavior affects trades;
- demo/dry-run behavior is verified before live-capable code is enabled;
- documentation is updated for new settings or workflows.

## Trading-specific gates
- New order or stop-update paths MUST have a dry-run mode.
- Live execution MUST be disabled by default.
- Risk engine MUST be called before any order placement/update action.
- Stale market data MUST block triggers and execution.
- User overrides MUST be logged.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 22; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-22"></a>

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
