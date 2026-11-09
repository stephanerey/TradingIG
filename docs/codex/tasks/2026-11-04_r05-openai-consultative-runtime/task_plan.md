# Plan — runtime OpenAI consultatif manuel

## Objectif vérifiable

Après validation de la connexion dans Settings, permettre un appel OpenAI manuel sur les seules
métadonnées officielles Fed/BCE déjà collectées, puis afficher l'analyse typée dans le ruban sans
modifier le scanner, le ticket, le risque ou l'exécution.

## Approche minimale

1. Projeter les `NewsItem` autorisés en preuves IA grises, sans score ni biais déterministe.
2. Autoriser ces preuves explicitement étiquetées comme citations IA, sans les rendre favorables
   dans le moteur macro.
3. Ajouter un worker Qt et une action manuelle de session, activée seulement après un probe réussi.
4. Afficher statut, biais, risque, modèle, confiance, sources et expiration dans le ruban.

## Limites

- Aucun appel automatique, recherche web autonome, article complet, donnée IG, ticket ou ordre.
- Le choix du modèle et l'autorisation restent limités à la session ; aucune migration de config.
- Les preuves brutes restent grises et n'influencent pas les agrégats déterministes.

## Skills

- `codex-tradingig-analysis-scanner` : provenance, états unknown et absence de chemin broker.
- `aurora-ui-visual-qa` : inspection du ruban et de l'action manuelle.

## Preuve prévue

- Régressions preuve news → contexte IA, worker non bloquant et activation manuelle.
- Suite complète, lint/format ciblés, rendu Qt Windows.
- Validation humaine du premier résultat consultatif réel.

## Suivi fraîcheur du 2026-11-06

- Skill : `codex-tradingig-analysis-scanner`.
- Borner les preuves news et la santé des sources à la date réelle de collecte, exclure les
  signaux futurs/expirés et ne pas lancer l'analyse IA sans preuve news encore admissible.
- Recalculer le contexte macro à l'heure de l'appel consultatif ; vérifier hors ligne sans nouvel
  appel réseau, changement de consentement ni chemin de trading.

## Suivi : portée et expiration du contexte

- Skill : `codex-tradingig-analysis-scanner`.
- Réévaluer les sources macro expirées à leur consommation par le Scanner et les projections produit.
- Refuser les analyses IA futures/expirées et les catalyseurs expirés à leur date limite exacte.
- Griser le ruban IA pour un marché différent ou à expiration via un minuteur Qt local sans appel réseau.
