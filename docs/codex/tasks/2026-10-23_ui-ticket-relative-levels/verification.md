# Vérification

## Résultats

- Baseline ciblée : `67 passed`.
- Régressions ticket/risque/shell : `69 passed`.
- Suite hors ligne complète : `213 passed in 11.61s`.
- Contrats et méthodes d'ordre IG protégés : `21 passed`.
- `ruff check src tests` : réussi.
- Format ciblé : réussi.
- Smoke Qt 960×600 : mode relatif actif, stop `40`, objectif `80`, aucun débordement
  horizontal, niveaux achat résolus `61/181` pour une entrée simulée `101`.
- Capture : `.codex_artifacts/ui-ticket-relative-levels-960x600.png`.

## Cas couverts

- Conversion relative achat et vente.
- Préremplissage `40/80`.
- Aller-retour relatif/absolu conservant les niveaux résolus lorsque le prix est disponible.
- Résumé affichant le mode et les niveaux absolus transmis au moteur.
- Vetoes risque, FX, KO et méthodes d'ordre IG inchangés.

