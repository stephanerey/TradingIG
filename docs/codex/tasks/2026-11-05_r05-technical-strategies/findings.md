# Findings

- Le registre et le replay sont prêts mais n'avaient aucune stratégie concrète.
- `IndicatorInput` ne contient ni spread, ni coûts, ni macro ; les stratégies techniques ne doivent
  donc pas prétendre les valider.
- `EVENT_DRIVEN` nécessite un input contexte distinct et sera traité séparément.
