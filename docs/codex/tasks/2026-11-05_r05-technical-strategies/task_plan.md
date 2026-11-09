# Plan — stratégies techniques PRD

## Objectif

Implémenter `TREND_FOLLOW`, `BREAKOUT` et `PULLBACK` comme stratégies déterministes configurables,
réutilisables par le registre et le replay, sans activation runtime ni broker.

## Contraintes

- Tous les paramètres sont explicites ; aucun profil de production implicite.
- Bougie de décision clôturée, horodatage/provenance et version de règles conservés.
- Warmup/invalidité et exclusions produisent un signal `FLAT` expliqué.
- Niveaux entrée/invalidation/cible sont des hypothèses techniques, pas des ordres.
- Spread, coûts, risque monétaire, contexte et exécution restent évalués par leurs composants
  séparés avant toute candidature.

## Preuves

- BUY, SELL, FLAT, warmup, extension, volume, volatilité, structure et configuration invalide.
- Registre, replay future-blind, suite complète et protections d'ordre.
