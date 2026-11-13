# Decisions

## D1 — aucune EMA synthétique

Une série EMA `READY` commence au timestamp de la bougie qui complète la période de
semence SMA. Aucun point n'est émis en `WARMING_UP` ou `INVALID`.

## D2 — même fermeture que le scanner

La dernière bougie est exclue comme potentiellement ouverte, puis seule la partie
temporellement continue est analysée.

## D3 — paramètres attestés

Les périodes rapide/lente sont lues dans la provenance `config:*` du signal. Aucune
période par défaut n'est injectée par l'interface.

