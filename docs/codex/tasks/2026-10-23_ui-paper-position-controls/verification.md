# Vérification

## Résultats

- Baseline ciblée : `58 passed`.
- Régressions Paper/session/GUI : `60 passed`.
- Suite hors ligne complète : `211 passed in 19.45s`.
- Contrats et méthodes d'ordre IG protégés : `21 passed`.
- `ruff check src tests` : réussi.
- Format des nouveaux fichiers ciblés : réussi.
- Smoke Qt hors écran 960×600 : position sélectionnée, contrôles stop/clôture visibles et actifs.
- Capture : `.codex_artifacts/ui-paper-position-controls-960x600.png`.

## Cas couverts

- Resserrement du stop confirmé et projeté dans la table.
- Élargissement du stop refusé et raison ajoutée au journal.
- Clôture manuelle locale confirmée, P&L réalisé et exposition libérée.
- Aucun adaptateur IG n'est importé ou appelé par la session Paper.

