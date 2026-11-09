# Plan — persistance et récupération Paper

## Objectif

Permettre une sauvegarde et une récupération **explicites** de la session Paper locale, sans
création automatique de base, sans secret et sans aucun chemin d'ordre IG.

## État du lot

Implémenté après validation humaine explicite du 2026-10-23. La base runtime par défaut est restée
absente pendant les contrôles ; toutes les preuves de migration et d'interface utilisent des
répertoires temporaires.

## Approche proposée

- Étendre le SQLite versionné existant avec des checkpoints Paper append-only.
- Sauvegarder uniquement sur action utilisateur.
- Restaurer le dernier checkpoint valide sans écraser silencieusement une session active.
- Vérifier checksum, version, UTC, Decimal texte et absence de secrets.
- Conserver l'interface provisoire ; aucune refonte GUI.

## Preuves obtenues

- Initialisation fraîche v2 et migration synthétique v1→v2 avec backup/restauration.
- Sauvegarde/rechargement d'une position ouverte et d'une position fermée.
- Rejet d'un checkpoint corrompu ou contenant une clé secrète.
- Append-only, checksum, rejet des secrets et absence d'I/O à l'import/démarrage.
- 221 tests hors ligne, 21 régressions protégées IG et `ruff check src tests` verts.

## Skills

- `codex-tradingig-storage-audit`
- `codex-tradingig-paper-execution`

