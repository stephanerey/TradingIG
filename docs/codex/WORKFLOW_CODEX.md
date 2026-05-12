# WORKFLOW_CODEX.md — Méthode de travail Codex pour projets Python

## 1. Compréhension
Avant de coder, Codex doit reformuler :

- objectif vérifiable ;
- symptômes ou besoin ;
- contraintes explicites ;
- fichiers ou modules probablement concernés ;
- risques techniques.

## 2. Sélection des skills
Choisir les skills pertinentes dans `docs/codex/SKILL_MAP.md`.
Ne pas tout charger.

## 3. Lecture minimale mais suffisante
Ordre recommandé :

1. `AGENTS.md`
2. `docs/CURRENT_STATE.md`
3. `docs/codex/CODEBASE_MAP.md`
4. `docs/codex/CODEBASE_MAP.generated.md`
5. fichiers ciblés
6. tests associés

## 4. Mémoire de tâche
Pour toute tâche non triviale :

```text
docs/codex/tasks/YYYY-MM-DD_slug/
  task_plan.md
  findings.md
  progress.md
  decisions.md
  verification.md
```

## 5. Plan avant patch
Le plan doit préciser :

- fichiers à lire ;
- fichiers susceptibles d'être modifiés ;
- commandes de vérification ;
- limite de périmètre ;
- ce qui ne sera pas fait.

## 6. Implémentation
Règles :

- patch minimal ;
- pas de refactor opportuniste ;
- pas d'ajout de dépendance sans justification ;
- tests ciblés d'abord ;
- respecter le style existant ;
- préférer fonctions/classes cohérentes avec l'architecture actuelle.

## 7. Vérification
Exécuter la vérification la plus proche du changement :

```bash
pytest tests/path/test_file.py -q
ruff check path/to/file.py
python -m package.module --help
python -c "import package"
```

Si impossible : documenter pourquoi dans `verification.md`.

## 8. Revue de diff
Avant clôture :

```bash
python scripts/codex/safe_diff_summary.py
```

Vérifier :

- fichiers modifiés attendus ;
- pas de secrets ;
- pas de fichiers générés inutiles ;
- imports cohérents ;
- tests ou impossibilité documentée ;
- mise à jour éventuelle de `CURRENT_STATE.md` et RepoMap.

## 9. Clôture
Réponse finale courte :

- ce qui a été fait ;
- fichiers modifiés ;
- vérifications exécutées ;
- limites restantes ;
- prochaine étape recommandée.
