# Verification

# Verification

- `ruff check` ciblé : vert.
- `ruff format --check` ciblé après formatage : vert.
- Tests calendrier/contexte/risque événementiel : `34 passed`.
- Régressions protégées IG REST/DEMO/AUTO : `27 passed`.
- Suite complète hors ligne : `345 passed`.
- Aucun appel Trading Economics réel, aucune clé ajoutée, aucune dépendance ou migration.
- L'adaptateur refuse les redirections, borne fenêtre/payload/événements, exige UTC et conserve
  `SourceUsageRights.UNKNOWN` par défaut jusqu'à confirmation contractuelle.

