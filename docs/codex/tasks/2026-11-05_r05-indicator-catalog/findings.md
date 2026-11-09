# Findings

- Le service existant couvre SMA, EMA, RSI et ATR seulement.
- MACD, Bollinger et niveaux nécessitent plusieurs sorties cohérentes ; les aplatir en une valeur
  unique perdrait l'auditabilité.
- Spread et signification du volume dépendent de données hors OHLC ; seul un ratio de volume fourni
  explicitement peut être calculé ici.
