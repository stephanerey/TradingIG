# Plan — preview Scanner GUI

## Objectif

Afficher manuellement les signaux techniques sur les bougies du graphique sans créer de score
incomplet, ticket ou ordre.

## Règles

- Exclure toujours la dernière bougie du chart, potentiellement ouverte.
- Profils initiaux explicitement étiquetés `preview`, non validés pour AUTO.
- Afficher stratégie, side, état, raisons, niveaux, validité et nombre de bougies utilisées.
- `EVENT_DRIVEN` reste inactif sans contexte événementiel qualifié.
- Aucun score 0..100 tant que les six composantes ne sont pas disponibles.

## Preuves

- Conversion Chart→Indicator, exclusion de la dernière bougie, warmup, ordre déterministe.
- Widget Qt et MainWindow sans chemin d'exécution.
- Suite complète et protections d'ordre.
