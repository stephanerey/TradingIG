# Vérification

- `ruff check src tests` : vert.
- `pytest -q` : 739 tests passés.
- Tests de priorité keyring/environnement et de suppression : verts.
- Test de persistance : aucune chaîne `api_key` ni valeur secrète dans `config.json`.
- Tous les transports de tests sont injectés ou mockés ; aucun appel réseau réel.
- Aucun ordre IG, activation automatique, abonnement ou paiement.
