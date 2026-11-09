# Barèmes des composantes Scanner

## Objectif

Appliquer l'échelle humaine commune `100/75/50/0/indisponible` aux cinq composantes restantes du
Scanner, sans fabriquer un score global lorsque des entrées manquent.

## Autorité et limites

- Seuils validés par l'utilisateur le 2026-11-05.
- Autorisé : contrats de score, évaluateurs déterministes, tests et documentation ciblée.
- Interdit : hypothèse silencieuse de frais nuls, score incomplet favorable, ticket, ordre,
  activation AUTO/LIVE, dépendance ou appel externe.

## Règles

- Technique : multi-stratégies concordantes 100, signal unique solide 75, fragile 50,
  contradiction 0 avec veto, données insuffisantes indisponibles.
- R/R conservateur : `>=3` 100, `>=2` 75, `>=1` 50, `<1` 0.
- Coûts/gain : `<=5 %` 100, `<=10 %` 75, `<=20 %` 50, au-delà 0.
- Qualité : fraîche/continue complète 100, dégradation légère 75, partielle 50,
  invalide/périmée/discontinue 0.
- Risque marché : très faible 100, normal 75, élevé 50, critique 0 avec veto.

## Skill

- `codex-tradingig-analysis-scanner`.
