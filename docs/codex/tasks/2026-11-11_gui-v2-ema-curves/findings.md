# Findings

- Le moteur central expose une valeur EMA scalaire mais pas sa série historique.
- La Watchlist transforme actuellement `fast_ema` et `slow_ema` du dernier signal en
  lignes horizontales, ce qui ne représente pas une moyenne mobile.
- Les mises à jour chart sont conservées par EPIC (maximum 500) et la dernière bougie
  peut être ouverte.
- Le scanner possède déjà la règle de continuité et d'exclusion de la bougie finale.
- Le graphique sait aligner les chandeliers en axe réel ou compressé via leur timestamp.

