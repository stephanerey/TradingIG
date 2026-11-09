# Plan — stratégie EVENT_DRIVEN

## Objectif

Implémenter un signal événementiel uniquement lorsque l'événement, le contexte directionnel et la
réaction de prix post-événement sont tous traçables et valides.

## Contrat

- Événement HIGH, publié/observé, droits connus, fraîcheur bornée et URL exigible par config.
- Assessment directionnel versionné, lié à l'ID événement et valide au temps de décision.
- Confirmation du prix après l'événement par impulsion/ATR ; gap trop grand = rejet.
- Aucune source ou direction manquante n'est devinée.
- Signal seulement, sans score, ticket, ordre ou activation runtime.

## Preuves

- BUY/SELL, droits inconnus, événement futur/ancien, contexte périmé, prix insuffisant,
  confirmation contradictoire et gap.
- Replay/registre, suite complète et protections d'ordre.
