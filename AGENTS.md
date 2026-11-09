# Repository Guidelines — TradingIG

## Mission
- Codex travaille comme agent de développement Python encadré.
- Objectif : patchs ciblés, vérifiables, sans refactor opportuniste.
- Ne pas coder si le besoin, les risques ou les sources de vérité ne sont pas clairs.

## Non-negotiable rules
- Répondre en français sauf demande contraire.
- Ne jamais afficher, committer ou documenter de secrets, tokens, credentials, clés API ou fichiers `.env`.
- Ne jamais casser l'architecture existante sans décision explicite.
- Ne pas ajouter de dépendance, service externe, tâche planifiée, accès réseau, stockage persistant ou migration sans validation.
- Ne pas inventer de règle métier non documentée.
- Ne pas masquer une erreur par fallback silencieux.
- Le code réel prime sur la documentation ; noter tout écart dans `findings.md`.
- Préférer un patch minimal à une réécriture globale.

## Python project rules
- Respecter le layout existant : `src/`, package racine, `tests/`, `scripts/`, `docs/`.
- Ne pas modifier l'environnement global Python ; utiliser le venv du projet.
- Ne pas déplacer des modules sans vérifier les imports, entry points et tests.
- Ne pas transformer un script fonctionnel en framework sans demande explicite.
- Toute modification de threading, asyncio, Qt, I/O matériel, trading ou données doit être justifiée et vérifiée.

## Source of truth
- `AGENTS.md` : garde-fous.
- `DESIGN.md` : conventions UX/CLI/desktop.
- `docs/CURRENT_STATE.md` : reprise projet.
- `docs/codex/PROJECT_PROFILE.yaml` : profil projet et commandes.
- `docs/codex/SKILL_MAP.md` : sélection des skills.
- `docs/codex/WORKFLOW_CODEX.md` : méthode détaillée.
- `docs/codex/CODEBASE_MAP.md` : carte humaine courte.
- `docs/codex/CODEBASE_MAP.generated.md` : carte générée.
- `docs/domain/` : règles métier.
- `docs/adr/` : décisions structurantes.

## Skill selection
Déclarer les skills dans `task_plan.md` avant toute tâche non triviale.

Skills méthode disponibles :
- `python-planning-with-files`
- `python-diagnose`
- `python-tdd`
- `python-review-diff`
- `python-architecture-check`
- `python-repomap-maintainer`
- `python-terminal-token-optimizer`
- `python-package-env`
- `python-pyqt-threading`
- `python-data-pipeline`
- `python-hardware-io`

## Planning with files
Pour toute tâche non triviale, créer ou mettre à jour :

```text
docs/codex/tasks/YYYY-MM-DD_slug/task_plan.md
docs/codex/tasks/YYYY-MM-DD_slug/findings.md
docs/codex/tasks/YYYY-MM-DD_slug/progress.md
docs/codex/tasks/YYYY-MM-DD_slug/decisions.md
docs/codex/tasks/YYYY-MM-DD_slug/verification.md
```

## RepoMap
Lire `docs/codex/CODEBASE_MAP.md` avant toute tâche multi-fichiers ou reprise. Consulter `CODEBASE_MAP.generated.md` pour identifier les modules, classes, fonctions, tests et scripts pertinents.

## Verification
Une tâche n'est terminée que si la vérification pertinente est exécutée ou si l'impossibilité est documentée dans `verification.md`.

Vérifications typiques :
- test ciblé : `pytest tests/path/test_x.py -q`
- lint : `ruff check .`
- typage optionnel : `mypy src` ou `pyright`
- import smoke : `python -c "import package"`
- app smoke : commande définie dans `PROJECT_PROFILE.yaml`

## Continuity rule
Clôture obligatoire : fait, fichiers modifiés, vérifications, risques, décisions, prochaine étape, besoin éventuel de mise à jour de `CURRENT_STATE.md` et RepoMap.

<!-- AURORA_SR_PACK_START -->
## SR Method 4.1

- Load `docs/codex/SR_BOOTSTRAP.md` only for a non-trivial mutation, a multi-lot run or a resume. Simple questions and local edits do not require the full method.
- Use `docs/codex/SR_ROUTES.json` to load only the procedure triggered by the task. Re-evaluate routes only when a new fact changes the scope.
- When the user explicitly requires validation before mutation, wait for that validation. One validation covers the bounded pass; do not add micro-gates while scope and safety remain unchanged.
- Do not create a failing test or red gate on purpose. Verify the final result with the least expensive evidence that covers the risk.
- Roll back only an activated runtime that is genuinely degraded and has a verified recovery candidate.
- In `core` knowledge mode, do not load or call MCP. In `nexus_kg` mode, follow `docs/codex/MCP_POLICY.yaml` and use only resolved, allowed capabilities.
- Store task state only when continuity is useful. Prefer one compact `task_state.yaml`; legacy contracts remain readable but are not required for new V4.1 tasks.
- Keep raw logs and large artifacts outside model context; inject bounded summaries and stable paths.
<!-- AURORA_SR_PACK_END -->
