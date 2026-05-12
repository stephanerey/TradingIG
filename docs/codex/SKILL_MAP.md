# SKILL_MAP.md — TradingIG

## Objectif
Aider Codex à sélectionner les skills utiles sans charger tout le contexte.

## Règle
Ne jamais charger toutes les skills par réflexe. Déclarer les skills choisies dans `task_plan.md`.

## Skills méthode Python

- `python-planning-with-files` : tâches non triviales, mémoire de tâche, continuité.
- `python-diagnose` : debug avant correction.
- `python-tdd` : test-first pragmatique ou test ciblé avant patch.
- `python-review-diff` : revue avant clôture.
- `python-architecture-check` : changements structurants.
- `python-repomap-maintainer` : mise à jour RepoMap.
- `python-terminal-token-optimizer` : sorties longues compactées, brut conservé.
- `python-package-env` : packaging, venv, dépendances, imports.
- `python-pyqt-threading` : PyQt/PySide, QThread, qasync, signaux/slots.
- `python-data-pipeline` : pandas/numpy/CSV/Parquet/ML léger.
- `python-hardware-io` : TCP, série, Modbus, SDR, instruments, I/O matériel.

## Quand sélectionner quoi ?

| Situation | Skills à déclarer |
|---|---|
| Bug runtime | `python-diagnose`, puis `python-review-diff` |
| Nouvelle fonction testable | `python-planning-with-files`, `python-tdd`, `python-review-diff` |
| Refactor/import/package | `python-package-env`, `python-architecture-check` |
| GUI PyQt/qasync | `python-pyqt-threading` |
| CSV/pandas/indicateurs | `python-data-pipeline` |
| Modbus/TCP/SDR/instrument | `python-hardware-io` |
| Sortie pytest/log très longue | `python-terminal-token-optimizer` |

## Skills métier Codex
À définir par projet :

```text
codex-{project}-core
codex-{project}-domain-rules
codex-{project}-ui
codex-{project}-hardware
codex-{project}-data
codex-{project}-safety
```

## Skills runtime
À distinguer des skills Codex : ce sont des agents ou outils embarqués dans l'application elle-même.
