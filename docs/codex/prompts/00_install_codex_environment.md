# Prompt Codex — installer et vérifier l'environnement méthode

Tu dois préparer l'environnement Codex du projet sans modifier le code applicatif.

## Objectifs
1. Lire `AGENTS.md`.
2. Lire `docs/CURRENT_STATE.md` s'il existe.
3. Lire `docs/codex/PROJECT_PROFILE.yaml`.
4. Vérifier les fichiers méthode avec `python scripts/codex/verify_codex_pack.py`.
5. Vérifier les skills avec `python scripts/codex/validate_skills.py --path ~/.codex/skills` ou équivalent Windows.
6. Générer le RepoMap avec `python scripts/codex/generate_python_repo_map.py --write`.
7. Ne pas modifier le code applicatif.

## Sortie attendue
- état de l'installation ;
- profil détecté ;
- commandes disponibles ;
- problèmes bloquants ;
- prochaine étape recommandée.
