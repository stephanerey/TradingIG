# Verification

- Ruff ciblé et format-check : verts.
- Tests calendrier/runtime/Settings/news/contexte : `46 passed`.
- Régressions protégées IG REST/DEMO/AUTO : `27 passed`.
- Suite complète hors ligne : `351 passed`.
- `git diff --check` ciblé : vert.
- La boucle Qt reste réactive pendant le probe synthétique lent.
- News et calendrier restent présents simultanément dans le ruban.
- `TRADING_ECONOMICS_API_KEY` est absente du processus local au moment de la clôture : aucune
  validation réseau réelle n'a été effectuée.
