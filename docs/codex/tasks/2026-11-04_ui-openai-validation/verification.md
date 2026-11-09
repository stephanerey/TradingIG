# Verification

## Résultats

- Tests ciblés OpenAI/service/GUI : `13 passed`.
- Suite complète : `313 passed`.
- Ruff ciblé sur les fichiers modifiés : vert.
- Format ciblé : vert.
- `git diff --check` : vert, hors avertissements CRLF préexistants.
- Rendu Windows inspecté à 700 × 560 : libellés, états, consentement et boutons lisibles sans
  débordement ; capture dans `.codex_artifacts/ui/openai-settings-windows.png`.

## Limites

- Aucun appel OpenAI réel n'a été exécuté pendant la vérification automatisée.
- `ruff check .` et `ruff format --check .` restent rouges sur des scripts SR et fichiers
  préexistants hors de ce patch ; les contrôles ciblés sont verts.
- La validation humaine doit relancer l'application puis utiliser Settings > OpenAI.

## Validation humaine

- 2026-11-04 : `OPENAI_API_KEY` détectée, modèle `gpt-6-luna`, plafond 600 tokens et
  acknowledgement explicite.
- Résultat affiché : connexion validée et réponse structurée reçue ; aucune donnée IG transmise.
