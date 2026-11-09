# Verification

- Tests OpenAI Settings/runtime ciblés : `4 passed in 2.68s`.
- Régressions protégées IG/connexion/streaming/risque/DEMO/ticket/Paper :
  `79 passed in 3.58s`.
- Suite hors ligne complète après clôture de la passe : `478 passed in 22.74s`.
- `ruff check src tests` : vert.
- Format des quatre fichiers Python modifiés : vert.
- Le format repository-wide reste rouge sur 10 fichiers préexistants hors de cette tâche ; aucun
  de ces fichiers n'a été reformatté.
- `git diff --check` : aucune erreur, seulement les avertissements LF/CRLF déjà présents.
- Aucun appel OpenAI réel, aucune connexion IG et aucune mutation broker pendant les tests.

