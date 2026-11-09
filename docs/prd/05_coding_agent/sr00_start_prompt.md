# SR00 Start Prompt — Separately Authorized Future Task

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstructed from the recovered V1.1.

**Last updated:** 2026-10-22

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 23; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-23"></a>

## 23. Premier prompt de démarrage Codex

> Tu travailles sur `stephanerey/TradingIG`, référence `codex/stream-live-candle-robustness` (`512c16d...`). Le PRD **V1.1** impose la **SR Method 4.1.0**. Première mission **SR00 uniquement** : examine l'installation SR héritée, sélectionne la source officielle `syl2042/Aurora_SR_method_codex_pack`, confirme `version=4.1.0` et `release_status=released`, vérifie l'état Git et génère un plan d'upgrade en lecture seule avec `--json`. **Présente les fichiers à modifier et préserver et attends ma validation explicite avant `--upgrade`.** Après autorisation séparée, applique exclusivement la migration SR, vérifie le résultat avec `sr_post_install_check`, puis arrête sans commencer le développement R00/R01 ni toucher aux ordres, au code métier ou aux secrets. Le prompt R00/R01 séparé ne sera utilisé qu'après SR00 satisfaisant.

---

**Sources techniques du projet et de la méthode :**

- Dépôt : <https://github.com/stephanerey/TradingIG>
- Branche auditée : <https://github.com/stephanerey/TradingIG/tree/codex/stream-live-candle-robustness>
- Findings des bougies : <https://github.com/stephanerey/TradingIG/blob/codex/stream-live-candle-robustness/docs/codex/tasks/2026-05-12_stream-live-candle-robustness/findings.md>
- PRD existant : <https://github.com/stephanerey/TradingIG/blob/codex/stream-live-candle-robustness/docs/prd/PRD.md>
- Consignes agent héritées : <https://github.com/stephanerey/TradingIG/blob/codex/stream-live-candle-robustness/AGENTS.md>
- SR Method 4.1.0 : <https://github.com/syl2042/Aurora_SR_method_codex_pack>
- Changelog officiel : <https://github.com/syl2042/Aurora_SR_method_codex_pack/blob/main/CHANGELOG.md>
- Guide français 4.1 : <https://github.com/syl2042/Aurora_SR_method_codex_pack/blob/main/INSTALLATION.fr.md>

**Fin du PRD V1.1 — méthode SR 4.1.0.**
