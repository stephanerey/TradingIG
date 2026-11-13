# GitHub checkpoint — journal de recherche technique

## État livrable

- journal append-only d'une évaluation par signal et d'un événement par échec ;
- compte IG pseudonymisé dans la base locale ;
- aucune modification des stratégies, scores ou seuils ;
- aucune création ou transmission d'ordre ;
- export anonymisé et atomique pour validation dans Rooms ;
- procédure de partage documentée dans `docs/ROOMS_VALIDATION_HANDOFF.md`.

## Vérification

- tests complets : `776 passed` ;
- Ruff ciblé sur les fichiers du lot : réussi ;
- essai CLI d'export : réussi, paquet vide attendu car l'application en cours
  d'exécution n'avait pas été relancée avec le nouveau recorder ;
- dette Ruff globale préexistante : 484 alertes dans les scripts SR hors lot.

## Première validation Rooms

1. relancer l'application depuis ce checkpoint ;
2. laisser au moins une bougie se fermer sur les valeurs suivies ;
3. générer le paquet avec `export-technical-validation` ;
4. déposer les trois fichiers produits dans Rooms ;
5. référencer l'identifiant d'événement dans chaque retour de validation.

## Hors périmètre de ce checkpoint

- calcul post-trade MFE/MAE ;
- association automatique d'un retour Rooms à un événement ;
- publication automatique vers Rooms ;
- exécution broker DEMO ou LIVE.
