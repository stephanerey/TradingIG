# Décisions

- D-001 : afficher `ALIGNÉ`, `PRUDENCE`, `DÉFAVORABLE` ou `INCONNU`, jamais une probabilité.
- D-002 : un risque événementiel élevé ou un composant directionnel opposé produit rouge ; un
  composant jaune produit prudence ; vert exige des composants disponibles sans veto.
- D-003 : l'IA expirée, indisponible ou hors scope reste grise et ne modifie pas l'agrégat.
- D-004 : le composant est informatif et n'alimente aucun ticket, ordre ou activation AUTO.
- D-005 : barème humain validé le 2026-11-05 : `CATALYSEUR=100` vert foncé, `ALIGNÉ=75` vert
  clair, `PRUDENCE=50` jaune, `DÉFAVORABLE=0` rouge et `INCONNU=indisponible` gris.
- D-006 : `CATALYSEUR` exige un signal `EVENT_DRIVEN` frais, directionnellement concordant,
  confirmé par le prix et traçable. Une actualité ou l'IA seule ne suffit pas ; un risque
  événementiel rouge conserve son veto.
- D-007 : décision humaine du 2026-11-05, les six composantes Scanner partagent les paliers
  `100/75/50/0/indisponible` et la palette vert foncé/vert clair/jaune/rouge/gris. Les critères
  propres à chaque composante restent distincts et traçables.
