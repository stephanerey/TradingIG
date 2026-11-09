# Findings

- Le runtime manuel existant utilise déjà un worker Qt, un secret redacted et un
  `MarketContextSnapshot` structuré sans dépendance broker.
- Le signal de validation transmet actuellement seulement modèle et plafond de sortie.
- Le PRD autorise l'exécution initiée par l'IA uniquement dans un futur mode `AUTO`, derrière Risk
  Engine, quotas, kill switch, expiration, journal et arrêt immédiat.
- La documentation OpenAI officielle recommande les Structured Outputs avec schéma JSON strict et
  le traitement explicite des refus/sorties incomplètes ; l'adaptateur existant suit déjà ce contrat.

