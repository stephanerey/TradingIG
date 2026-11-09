# Findings

- F011 spécifie un ruban global persistant.
- F004/F005 prévoient la consommation des mêmes drapeaux par ligne de Scanner, mais la liste de
  découverte produits ne les projetait pas encore.
- L'analyse OpenAI courante est soit globale, soit liée à l'EPIC sélectionné ; elle ne doit pas être
  recopiée sur d'autres produits quand son scope ne correspond pas.
- Les noms IG français `Achat`/`Vente` peuvent compléter un champ direction encore `unknown` pour
  la seule projection d'alignement, sans muter les métadonnées broker.
