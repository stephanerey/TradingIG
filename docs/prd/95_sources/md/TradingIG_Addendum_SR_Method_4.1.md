# Addendum de livraison — SR Method 4.1.0 dans TradingIG

**20 octobre 2026 — PRD V1.1 / SR 4.1.0**

La version V1.0 du PRD ne mentionnait pas explicitement SR 4.1.0. Cette V1.1 ajoute le chapitre §18.3, une phase SR00 préalable à R00–R08, des critères `AC-SR-001..006` et deux prompts Codex distincts.

- **SR00 :** migration de la méthode seule, lecture seule puis preview, validation humaine, upgrade, post-check, arrêt.
- **R00/R01 :** reprise de l'application seulement **après** SR00 réussi et explicitement accepté.
- **Version officielle source :** 4.1.0, `released`, 24/09/2026. Le commit réellement utilisé sera relevé par Codex lors de la preview.
- **Règles principales :** `AGENTS.md` court et réconcilié ; routes conditionnelles ; Scope, Verification, Activation ; skills spécialisés sur déclencheur ; `task_state.yaml` compact lorsque nécessaire ; préservation des contrats historiques ; MCP `core` désactivé.
- **TradingIG :** la sécurité d'ordre et les tests unitaires critiques restent requis, malgré l'abandon du rituel TDD par SR 4.1 ; aucune opération live, migration ou activation pendant SR00. Contrôle graphique natif PyQt5 Windows.

**Important :** le PRD et son pack n'installent pas la SR Method dans GitHub. Ils prescrivent son installation contrôlée par Codex et le point d'arrêt humain. Le dépôt n'a pas été modifié pour cette mise à jour de spécification.

**Références officielles :**
- https://github.com/syl2042/Aurora_SR_method_codex_pack
- https://github.com/syl2042/Aurora_SR_method_codex_pack/blob/main/INSTALLATION.fr.md
- https://github.com/syl2042/Aurora_SR_method_codex_pack/blob/main/CHANGELOG.md
- https://github.com/syl2042/Aurora_SR_method_codex_pack/blob/main/core/SR_METHOD.md
