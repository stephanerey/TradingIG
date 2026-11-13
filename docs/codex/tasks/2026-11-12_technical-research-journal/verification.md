# Verification

## Automated

- `python -m ruff check` ciblé sur le recorder, l'export, le câblage, la
  persistance, le CLI et leurs tests : **passed**.
- `python -m pytest -q` : **776 passed in 79.26s**.
- `git diff --check` : aucune erreur d'espace ; avertissements CRLF uniquement.
- export CLI réel vers `.codex_artifacts/rooms-validation-checkpoint-2026-11-12` :
  **passed**, 0 événement car le processus GUI en cours n'avait pas chargé le
  nouveau recorder.

## Limitation connue hors lot

Le Ruff global signale 484 erreurs préexistantes dans `scripts/codex`. Elles ne
concernent pas les fichiers applicatifs de ce lot et n'ont pas été modifiées.

## Human validation

Pending grouped validation after restarting this checkpoint and closing at
least one new candle.

