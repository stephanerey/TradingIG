# Plan — résolution des profils Scanner

## Objectif

Résoudre des paramètres Scanner selon la priorité humaine `global -> compte -> stratégie -> marché`,
avec origine inspectable de chaque valeur, sans UI, persistance ni chemin d'exécution.

## Approche minimale

- Partir d'un `ScannerStrategyProfile` complet et valide.
- Appliquer des patches explicites, identifiés et limités à des chemins de feuilles connus.
- Revalider le profil complet après chaque résolution et conserver l'origine finale par chemin.
- Fournir le profil résolu au cœur multi-marchés existant sans modifier le broker, le ticket ou le
  Risk Engine.

## Skill

- `codex-tradingig-analysis-scanner` : provenance, configuration explicite et séparation broker.

## Preuves prévues

- Priorité, chemins imbriqués, origine, immutabilité et invalidité.
- Tests Scanner ciblés, protections ordre/risque, suite complète et Ruff.

