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

- `codex-tradingig-accounts-risk` — `docs/codex/project-skills/codex-tradingig-accounts-risk/SKILL.md` ; utiliser pour les comptes, paramètres de risque, tickets, expositions, réservations et vetoes financiers.
- `codex-tradingig-storage-audit` — `docs/codex/project-skills/codex-tradingig-storage-audit/SKILL.md` ; utiliser pour SQLite, journal append-only, agrégations P&L, paramètres atomiques, sauvegarde et restauration.
- `codex-tradingig-analysis-scanner` — `docs/codex/project-skills/codex-tradingig-analysis-scanner/SKILL.md` ; utiliser pour indicateurs, stratégies, contexte macro, scoring, classement et commentaires explicables.
- `codex-tradingig-paper-execution` — `docs/codex/project-skills/codex-tradingig-paper-execution/SKILL.md` ; utiliser pour PaperBroker, tickets simulés, pending logiciels, transitions de trade, protections et replay.
- `codex-tradingig-supervised-demo-gate` — `docs/codex/project-skills/codex-tradingig-supervised-demo-gate/SKILL.md` ; utiliser pour les preuves IG DEMO authentifiées, la matrice de capacités, la réconciliation et les gates d'exécution supervisée avec refus LIVE par défaut.

## Skills runtime
À distinguer des skills Codex : ce sont des agents ou outils embarqués dans l'application elle-même.

<!-- AURORA_SR_PACK_START -->
## SR Method 4.1 skills

Skills metier Codex et Skills runtime doivent etre declares ici ou dans `PROJECT_PROFILE.yaml`.

Par defaut :

- `aurora-diagnose`
- `aurora-ui-visual-qa`
- `aurora-architecture-check`
- `aurora-lot-runner`

Facultatives :

- `aurora-domain-skill-factory`
- `aurora-to-prd`

Consulter `docs/codex/SKILL_DIGEST.md` seulement quand une de ces specialisations peut s'appliquer. Le planning, la compaction terminal, la revue finale et RepoMap sont des mecanismes du harness, pas des skills cognitives. SR 4.1 n'impose aucun TDD ni test rouge volontaire.

## Knowledge mode

- `core` : utiliser RepoMap puis lecture ciblee du code reel.
- `nexus_kg` : utiliser RepoMap + Nexus KG, puis lecture ciblee du code reel.

Les skills metier Codex restent locales au projet sauf decision explicite. Une skill projet non declaree dans ce fichier ou dans `PROJECT_PROFILE.yaml` est interdite par defaut.
<!-- AURORA_SR_PACK_END -->
