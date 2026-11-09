# Verification

- Tests EVENT_DRIVEN : `8 passed`.
- Tests indicateurs/4 stratégies/scoring/replay : `49 passed`.
- Régressions protégées IG REST/DEMO/AUTO : `27 passed`.
- Suite complète hors ligne : `378 passed`.
- Ruff, format et `git diff --check` ciblés : verts.
- Droits inconnus, contexte absent/périmé, événement futur/ancien, historique incomplet, gap et
  confirmation prix contradictoire restent FLAT.
- Aucun runtime, ticket ou ordre.
