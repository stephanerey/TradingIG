# Vérification

- `python -m ruff check src tests` : vert.
- tests ciblés config/persistance/session/ticket/UI : `84 passed`.
- suite complète hors ligne : `221 passed`.
- protections IG `test_ig_rest_adapter.py` + `test_adapter_contracts.py` : `21 passed`.
- migration synthétique v1→v2 : backup créé, journal conservé, historique de versions `1,2`.
- checkpoint : append-only, checksum, rejet des clés secrètes, Decimal texte et UTC.
- Qt offscreen : base absente avant action, sauvegarde explicite, nouvelle fenêtre vide puis
  restauration explicite d'une position ouverte et de son audit.
- aucun appel IG, aucune mutation DEMO/LIVE, aucune dépendance ajoutée.
- base runtime par défaut non créée par les contrôles.

