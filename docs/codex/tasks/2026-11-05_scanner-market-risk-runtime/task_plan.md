# Risque marché runtime du Scanner

## Objectif

Raccorder le risque événementiel normalisé existant au composant Risque du Scanner sans confondre
opportunité directionnelle et sécurité de marché.

## Barème validé

- `HIGH` → critique, 0, veto.
- `MEDIUM` → élevé, 50.
- `LOW` → normal, 75.
- `UNKNOWN` → indisponible.
- Aucun 100 automatique sans preuve dédiée de faible risque.

## Limites

Aucun ticket, ordre, appel externe ou activation LIVE/AUTO. Skill :
`codex-tradingig-analysis-scanner`.
