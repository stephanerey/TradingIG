# TradingIG — transfert de validation vers Rooms

Ce jalon permet de partager les décisions du moteur technique sans publier la
base locale ni des données de compte IG. Le transfert vers Rooms reste une
action humaine explicite : l'application ne publie rien automatiquement.

## 1. Générer le paquet anonymisé

Il faut d'abord relancer l'application avec cette version, puis attendre au
moins une nouvelle évaluation sur bougie close. Une application restée ouverte
pendant la mise à jour ne charge pas rétroactivement le nouveau journal.

Depuis la racine du dépôt, après cette session de validation :

```powershell
.\.venv\Scripts\python.exe -m trading_ig_assistant.main export-technical-validation `
  --output "$env:USERPROFILE\Documents\TradingIG-validation-2026-11-12"
```

La commande lit par défaut la base locale de simulation utilisée par
l'application. Une base différente peut être indiquée avec `--database`.
Le dossier de destination doit être inexistant afin d'éviter tout écrasement.
Un export à zéro événement est valide mais signifie qu'aucune nouvelle
évaluation technique n'a encore traversé le journal dans cette version.

## 2. Contenu à déposer dans Rooms

- `README.md` : périmètre, confidentialité et grille de validation ;
- `summary.json` : compteurs par environnement, stratégie et état ;
- `technical-events.jsonl` : une ligne immuable par évaluation ou échec.

Le paquet exclut l'identifiant de compte IG, le PnL, les tickets, les ordres,
les positions et les secrets. Les événements conservent les bougies closes,
indicateurs, états de préparation, niveaux, raisons et provenances utiles à
l'analyse post-mortem.

## 3. Ce qui va dans GitHub

Le code, les tests et cette procédure peuvent être poussés dans GitHub. Les
paquets de validation générés ne doivent pas être commités : ils sont destinés
au partage contrôlé dans Rooms.

## 4. Grille de retour conseillée dans Rooms

Pour chaque cas discuté, noter :

1. l'instrument, l'heure UTC, la stratégie et l'identifiant d'événement ;
2. `signal correct`, `signal manqué`, `faux signal` ou `données insuffisantes` ;
3. la cohérence de l'entrée, de l'invalidation et de l'objectif ;
4. les indicateurs ou éléments de contexte qui justifient le retour ;
5. l'amélioration proposée, sans modifier directement les seuils de production.

Les scores du scanner sont des rangs explicables et non des probabilités. Tout
changement de stratégie issu de ces retours doit rester versionné, testé hors
ligne et validé humainement avant d'influencer la simulation.
