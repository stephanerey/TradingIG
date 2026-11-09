# Decisions

- Clé lue depuis `TRADING_ECONOMICS_API_KEY`, jamais depuis le JSON applicatif.
- Validation et activation limitées à la session courante.
- Pays et fenêtres pré/post sont visibles et explicites.
- Un succès réseau ne change pas automatiquement les droits d'utilisation : `UNKNOWN` demeure le
  défaut conservateur.
