# Réglages du score Scanner

## Objectif

Rendre éditables et persistants les six poids et les seuils globaux définis par le PRD, puis les
raccorder au calcul déterministe du Scanner.

## Valeurs initiales PRD

- Poids : Technique 30, Contexte 15, R/R 20, Risque 15, Coûts 10, Qualité 10.
- Candidate ≥ 75, Watch ≥ 60, Reject/NO_TRADE sous 60.
- Une composante inconnue bloque toujours le score total.

## Limites

Configuration globale uniquement ; aucun nouvel héritage, ticket, ordre ou AUTO/LIVE. Skill :
`codex-tradingig-analysis-scanner`.
