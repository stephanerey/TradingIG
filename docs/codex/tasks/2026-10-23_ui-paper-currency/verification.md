# Verification

## Résultats

- Baseline ciblée avant mutation : `57 passed`.
- Régressions ciblées ticket/risque/shell : `62 passed`.
- Suite hors ligne complète : `209 passed in 11.00s`.
- Régressions protégées des méthodes d'ordre IG : `13 passed`.
- `ruff check src tests` : succès.
- `ruff format --check` sur le ticket et ses tests : succès.
- Smoke Qt offscreen exact à 960×600 : produit Barrière sans devise, champ `EUR` éditable,
  proposition approuvée, bouton Paper actif, défilement horizontal maximal `0`.
- Capture locale : `.codex_artifacts/ui-paper-currency-960x600.png`.

## Cas couverts

- métadonnée devise connue : valeur visible et verrouillée ;
- métadonnée absente : refus tant qu'un code alphabétique de trois lettres n'est pas confirmé ;
- confirmation EUR : validation possible avec niveaux/risk valides ;
- devise non-EUR sans FX : veto `fx_incomplete` conservé ;
- devise non-EUR avec taux explicite : évaluation autorisée selon les autres règles.

Aucune devise/taux n'est inféré, aucune connexion réseau n'est ajoutée et aucune protection
d'exécution IG n'est modifiée.

