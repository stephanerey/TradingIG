# Decisions - stream live candle robustness

- Limiter les modifications de cette tache a la memoire Codex demandee.
- Ne pas executer de tests applicatifs pendant cette analyse: la demande est lecture seule hors memoire de tache, et pytest peut produire des caches locaux.
- Ne pas analyser ni modifier le backfill REST, les retries historiques, l'allowance history ou `IGRestAdapter`.
- Prioriser un patch futur qui garde la lecture du stream-cache disponible meme quand le REST historique est bloque.
