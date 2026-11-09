# Cœur Scanner multi-marchés

## Objectif

Évaluer plusieurs marchés dans un service indépendant du GUI et du broker, conserver les résultats
par stratégie et produire un classement global déterministe.

## Limites

- Entrées déjà disponibles en mémoire uniquement ; aucun fetch réseau ou historique.
- Un échec marché reste local et traçable.
- Aucun ticket, ordre, broker, rafraîchissement automatique ou widget.
- Skill : `codex-tradingig-analysis-scanner`.
