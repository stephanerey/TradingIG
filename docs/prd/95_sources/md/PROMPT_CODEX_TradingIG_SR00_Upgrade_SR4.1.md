# TradingIG — Premier prompt Codex : SR00 (upgrade SR 4.1.0 uniquement)

Dépôt : `stephanerey/TradingIG` ; base fonctionnelle à préserver : `codex/stream-live-candle-robustness` (`512c16d59337d2b92bb475daecb96cc902eb00c0` lors de l'audit). Références : `PRD_TradingIG_V1.1_SR4.1_2026-10-20.md` §18.3 et `TradingIG_Audit_Reprise_2026-10-20.md`.

**Objectif vérifiable :** examiner l'ancienne installation SR/Codex du dépôt et produire une prévisualisation de migration **vers la release officielle 4.1.0** ; **ne pas modifier un fichier avant validation humaine du plan**.

Source SR officielle : https://github.com/syl2042/Aurora_SR_method_codex_pack
Guide officiel : https://github.com/syl2042/Aurora_SR_method_codex_pack/blob/main/prompts/fr/05_upgrade_codex_environment.md

## Première réponse attendue — lecture seule uniquement

1. Confirmer répertoire, branche, commit, statut Git, fichiers non committés et éventuels écarts de la base fonctionnelle. Ne pas fusionner `main`.
2. Lire `AGENTS.md`, `docs/CURRENT_STATE.md`, `docs/codex/PROJECT_PROFILE.yaml`, `docs/codex/SKILL_MAP.md` et tous les marqueurs/version SR disponibles ; détecter l'installation existante sans supposer sa version.
3. Récupérer la source officielle SR dans un répertoire local **hors code applicatif** ; documenter URL, branche, `source_commit`, `core/SR_PACK_VERSION.json` (`4.1.0`, `released`) et état Git. Ne pas exécuter un installateur depuis une source inconnue.
4. Lire `INSTALLATION.fr.md` et `prompts/fr/05_upgrade_codex_environment.md` dans la source officielle.
5. Générer la prévisualisation : `python <SR_PACK_SOURCE>/scripts/install_codex_pack.py --source <SR_PACK_SOURCE> --target <TradingIG> --json` ; classifier précisément les chemins `absent / managed / locally_modified / unmanaged / obsolete / conflict / already_aligned`.
6. Répertorier protections : code `src/`, tests métier, `pyproject.toml`, secrets, `.env`, DB/migrations, `docs/prd/`, mémoire `docs/codex/tasks/`, lots/passes/inbox, docs et compétences locales, règles hors bloc SR géré.
7. Présenter le plan d'upgrade, conflits, fichiers préservés, correctifs sûrs proposés et toute suppression envisagée. **Attendre la validation explicite du plan ; STOP.**

## Après validation distincte de ce plan

- Utiliser le mode officiel `--upgrade` (pas `--write` sur installation existante). Ne faire que l'évolution de la méthode ; ne pas modifier l'application.
- Exécuter `python scripts/codex/sr_post_install_check.py --root . --json`, les vérificateurs réellement présents, `git diff --check` et `git status --short`.
- Vérifier `SR_PACK_VERSION.json=4.1.0`, le noyau AGENTS court, routes, digest skills, policy MCP, mémoire existante préservée.
- Évaluer si un réalignement SR mémoire est nécessaire ; si oui, proposer la sous-phase séparée selon `prompts/fr/07_realign_sr_state_after_upgrade.md`.
- Rapporter preuves, versions, chemins, conflits et éléments non vérifiés. **Arrêter avant tout développement R00/R01**, build, ordre IG, activation de connexion métier ou déploiement.

## Particularités TradingIG

- La méthode **SR 4.1.0** retire le TDD imposé et les anciens skills de planification/terminal/RepoMap ; ne pas restaurer les anciens catalogues comme compétences obligatoires.
- Garde-fous produit non négociables : aucun ordre réel, aucun secret exporté, aucun changement de logique du risque, des comptes, de l'OHLC ou du streaming dans cette phase.
- `knowledge.mode` reste `core` (aucun outil MCP activé par le protocole SR) sauf validation explicite future.
- Ne pas créer de skills locaux métier ni de lots applicatifs sans validation ; préserver les mémoires anciennes.
