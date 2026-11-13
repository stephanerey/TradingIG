# Verification

- `ruff check` ciblé : OK.
- `pytest` ciblé indicateurs/Watchlist/ChartView : 107 tests réussis.
- Le RSI 14 exige 15 bougies clôturées continues.
- Aucun point partiel n'est publié pendant `WARMING_UP`.
- Le panneau reste borné à 0–100 et disparaît explicitement si indisponible.
- Régression complète : 764 tests réussis.
- Validation visuelle : à grouper avec les courbes EMA.
