# Plan — courbes EMA historiques GUI V2

## Objectif

Remplacer les lignes EMA horizontales issues du dernier signal par des courbes EMA
horodatées, calculées par le service technique central sur les seules bougies clôturées,
continues et attestées de la session affichée.

## Périmètre autorisé

- Domaine et service d'indicateurs techniques.
- Projection des mises à jour chart vers une entrée technique clôturée.
- Superpositions du graphique Watchlist et tests associés.
- Documentation SR et RepoMap si la structure change.

Hors périmètre : ordre IG, activation automatique, backfill réseau, historique inventé,
modification des paramètres de stratégie.

## Hypothèses

- La dernière bougie de la série reste potentiellement ouverte et doit être exclue.
- Les périodes EMA proviennent exclusivement de la provenance du signal sélectionné.
- Une rupture temporelle conserve seulement le suffixe continu, comme le scanner.

## Approche minimale

1. Ajouter un contrat immuable de série d'indicateur et une fonction `ema_series`.
2. Construire l'entrée technique à partir des mises à jour chart de la Watchlist.
3. Ajouter au graphique un overlay de série aligné par timestamp.
4. Retirer les EMA des niveaux horizontaux et piloter leur disponibilité réelle.
5. Vérifier par tests unitaires ciblés, lint, suite complète et audit SR.

## Skills

- Aucun skill hôte ne correspond exactement à la méthode Python locale ; application
  directe des procédures SR 4.1 `mutation`, `architecture`, `ui`, `pass`, `resume` et
  `verification`.

