# Decisions

- Un patch modifie uniquement des feuilles nommées ; remplacer silencieusement une configuration
  complète est interdit.
- Chaque patch a un identifiant non vide et chaque origine expose couche + identifiant.
- Le résolveur ne choisit pas les patches applicables et ne persiste rien : le schéma de sélection
  reste un lot distinct.

