# Indicateur de contexte par produit

## Objectif

Afficher sur chaque Barrière/Option la projection conservatrice du contexte marché déjà normalisé,
puis exposer le barème humain validé comme composante explicable du futur score Scanner, sans en
faire une recommandation de trade.

## Autorité et périmètre

- Demande humaine explicite du 2026-11-05 de continuer jusqu'à une validation/question nécessaire.
- Autorisé : contrat de projection, colonne GUI provisoire, tests et documentation ciblée.
- Interdit : activation AUTO/LIVE, ordre broker, nouvel appel externe, dépendance ou migration.
- Préserver tous les changements locaux préexistants.

## Approche minimale

1. Comparer le biais index/or/régime au sens long/court du produit.
2. Ajouter le risque événementiel et l'IA uniquement si son scope couvre le produit.
3. Faire dominer le risque rouge et conserver toute donnée absente en gris/inconnu.
4. Exposer composants, raisons et provenance en infobulle dans la découverte et le Scanner.
5. Exposer uniquement la composante contexte pondérée 15 %, sans fabriquer les cinq autres
   composantes ni un score global incomplet.
6. Ne modifier ni le ticket Paper, ni les signaux techniques, ni l'exécution.

## Skill sélectionnée

- `codex-tradingig-analysis-scanner` : contexte manquant explicite, provenance, score non
  probabiliste et absence de chemin broker.
