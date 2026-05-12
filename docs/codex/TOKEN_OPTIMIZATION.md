# TOKEN_OPTIMIZATION.md

## Objectif
Réduire les tokens consommés par les sorties terminal longues sans perdre l'information utile.

## Principe
- La sortie brute est conservée localement.
- Codex ne lit que le résumé compact sauf besoin.
- En cas d'échec incompris, Codex relit le brut ciblé.

## Commande recommandée

```bash
python scripts/codex/python_token_run.py -- pytest -q
python scripts/codex/python_token_run.py -- ruff check .
```

## Sorties brutes

Par défaut :

```text
.codex_artifacts/command_logs/
```

## Quand utiliser

- pytest très long ;
- logs applicatifs ;
- `git diff` volumineux ;
- scans de fichiers ;
- commandes réseau ou matériel bavardes ;
- build ou packaging.

## Quand ne pas utiliser

- commande courte ;
- erreur concise ;
- sortie dont chaque ligne est significative.
