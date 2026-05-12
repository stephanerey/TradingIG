# REPO_MAP_POLICY.md

## Objectif
Maintenir une carte légère du codebase pour éviter que Codex lise trop de fichiers et consomme trop de tokens.

## Fichiers

```text
docs/codex/CODEBASE_MAP.md           # carte humaine courte
docs/codex/CODEBASE_MAP.generated.md # carte générée automatiquement
```

## Quand consulter le RepoMap

- reprise de projet ;
- tâche multi-fichiers ;
- bug sans fichier évident ;
- refactor ;
- ajout de fonctionnalité ;
- modification d'architecture.

## Quand régénérer

```bash
python scripts/codex/generate_python_repo_map.py --write
```

À faire si :

- module ajouté/supprimé ;
- package renommé ;
- script important ajouté ;
- test ajouté ;
- entry point modifié ;
- layout modifié ;
- ressource Qt ajoutée ;
- configuration pyproject/requirements modifiée.

## Règles

- Ne pas transformer le RepoMap en documentation exhaustive.
- Ne pas y mettre de secrets, chemins locaux sensibles ou données privées.
- La carte générée peut être écrasée.
- La carte humaine doit rester courte et maintenue manuellement.
