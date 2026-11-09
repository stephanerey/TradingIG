# Findings

- `ScannerStrategyProfile` contient déjà les configurations typées complètes des trois stratégies.
- `MarketScannerInput` accepte déjà un profil résolu par marché.
- La priorité `global -> compte -> stratégie -> marché` est validée par D-013 et déjà appliquée aux
  paramètres de risque.
- Le PRD n'impose pas encore de schéma de stockage pour les sélecteurs compte/stratégie/marché ; ce
  lot ne l'invente pas.

