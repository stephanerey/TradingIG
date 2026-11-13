# Verification

- `ruff check` ciblé : OK.
- `pytest` ciblé domaine/service/Watchlist/ChartView : 104 tests réussis.
- Couverture ajoutée :
  - amorçage SMA et alignement temporel d'une série EMA ;
  - absence de points en phase WARMING_UP ;
  - mapping exact des timestamps sur axes compressé et réel ;
  - remplacement des niveaux EMA horizontaux par deux courbes dans la Watchlist.
- Régression complète : 761 tests réussis.
- Validation visuelle : à effectuer dans l'application avec au moins 22 bougies
  clôturées continues.

