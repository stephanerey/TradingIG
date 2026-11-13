# Constats

- Les calculs existaient déjà dans `indicator_service.py` mais seules certaines
  valeurs recopiées dans le signal sélectionné atteignaient le GUI.
- Un widget ne doit pas reconstruire EMA, RSI, ATR ou support/résistance.
- La provenance disponible contient timeframe, source, base de prix et période.
- Une courbe historique ne peut être dessinée à partir de la seule dernière
  valeur sans inventer des points intermédiaires.
