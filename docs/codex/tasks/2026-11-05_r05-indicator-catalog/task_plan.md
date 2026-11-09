# Plan — catalogue d'indicateurs PRD

## Objectif vérifiable

Compléter le service d'indicateurs déterministes avec MACD, Bollinger, momentum, ROC, niveaux
récents, volatilité réalisée et ratio de volume/tick-volume, sans stratégie, score ni broker.

## Règles

- Bougies UTC ordonnées et clôturées uniquement.
- `WARMING_UP` ou `INVALID` sans valeur fabriquée.
- Paramètres explicites et provenance conservée.
- Résultats multi-valeurs typés pour MACD/Bollinger/niveaux.
- Aucune interprétation directionnelle ni promesse de performance.

## Preuves

- Fixtures numériques, historique insuffisant, OHLC/temps invalide, volume manquant et divisions
  impossibles.
- Ruff, suite complète et régressions d'ordre protégées.
