# Verification

## Résultats

- Tests ciblés du correctif Structured Outputs et diagnostic Qt : `33 passed` (`18 + 15`).
- Suite complète après correction de rotation Windows : `319 passed`.
- Ruff et format ciblés sur les 13 fichiers Python affectés : verts.
- Rendu Windows du ruban à 1 440 px : les six chips sont lisibles, avec contexte IA séparé ;
  capture `.codex_artifacts/ui/openai-consultative-ribbon.png`.
- Aucun appel OpenAI réel, appel IG ou mutation Paper n'a été exécuté par l'automatisation.
- Le schéma limite désormais `source_signal_ids` à 1–5 identifiants exacts issus des preuves
  admissibles ; les signaux `data_health` en sont exclus.
- En cas de nouvelle dégradation, la barre d'état, l'infobulle du chip IA et le log affichent
  uniquement un code sûr `AI_*`, sans réponse brute ni secret.
- Validation humaine du 2026-11-05 : résultat consultatif disponible avec
  `openai-responses:gpt-6-luna`, biais et risque `unknown`, sans ticket ni ordre.
- Régression de rotation : une erreur `PermissionError` simulée diffère le rollover et la ligne de
  log est toujours écrite.
- Validation humaine du 2026-11-05 après redémarrage : plus aucune erreur de rotation du log.
- Suivi fraîcheur du 2026-11-06 : 40 tests ciblés news/IA/macro, 57 tests de protection et 585 tests
  complets réussis ; Ruff src/tests vert. Collecte expirée/future, expiration exacte, payload IA et
  absence d'appel sans preuve active couverts par fixtures ; aucun appel réseau exécuté. Validation
  Windows groupée après redémarrage encore à effectuer.
- Avant un nouveau refresh des sources, le ruban recalcule désormais l'état de collections déjà
  expirées même si la collecte suivante est lente ou indisponible. Dernier contrôle : 41 tests
  ciblés, 57 tests de protection, 586 tests complets et Ruff src/tests réussis. Aucun appel OpenAI
  ou IG authentifié effectué par les tests.
- Suivi portée/expiration : 36 tests ciblés projection/Scanner/IA, 57 tests de protection et 589
  tests complets réussis ; Ruff src/tests vert. Les tests couvrent risque macro expiré, analyse
  future/expirée, catalyseur à expiration, changement de marché et expiration visuelle Qt sans
  appel fournisseur. Reste à valider visuellement avec le reste du lot après redémarrage.

## Limites

- Le choix du modèle n'est pas persisté : le probe Settings doit être refait après redémarrage.
- Le runtime ne dispose encore ni de calendrier macro structuré ni des proxies USD/taux/VIX/pétrole.
