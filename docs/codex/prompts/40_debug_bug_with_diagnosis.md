# Prompt Codex — debug avec diagnostic obligatoire

Tu dois corriger un bug Python sans patch au hasard.

## Étapes
1. Décrire le symptôme.
2. Lister 2-4 hypothèses maximum.
3. Lire les fichiers ciblés.
4. Trouver une preuve pour/contre chaque hypothèse.
5. Identifier la cause probable.
6. Proposer un patch minimal.
7. Ajouter ou lancer un test ciblé si possible.
8. Revoir le diff.

## Interdictions
- Refactor global.
- Fallback silencieux.
- Catch `Exception` sans log utile.
- Changement d'architecture non demandé.
