# Decisions

- Ne pas sélectionner de fournisseur calendrier dans ce lot.
- Ne pas convertir `MEDIUM`, `LOW` ou `UNKNOWN` en sévérité implicite.
- Exiger les fenêtres de pré-alerte et de maintien post-événement à chaque appel.
- Utiliser un score nul uniquement pour signifier « non directionnel », avec le tag `event` qui
  alimente séparément le risque événementiel.

