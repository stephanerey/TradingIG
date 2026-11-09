# 09 — Diagnostics, surveillance, alertes et paramètres

## Objectifs

Avoir une interface fiable quand l'application tourne longtemps : chaque dépendance externe, source de données et calcul significatif expose une **santé vérifiable**. Tous les réglages utilisateur sont accessibles depuis l'UI avec validation, persistance et sécurité.

## A. Santé et diagnostics

Sous-onglets `Santé des services`, `Flux / quotas`, `Incidents`, `Journaux`.

### Table de diagnostic suggérée

| Service | États à distinguer | Signal de santé probant | Action sans risque |
|---|---|---|---|
| IG REST | connecté / token expiré / erreur / hors ligne | probe contrôlé / dernière réussite / latence / code | Tester en lecture seule |
| IG Streaming | connecté / souscrit / droit refusé / stale | transport + abonnement + âge last tick par EPIC | Resouscrire selon quotas |
| Bougies / OHLC | ready / warmup / gap / fallback | nombre, timeframe, source, continuité, âge | Détail série |
| Scanner | prêt / incomplet / erreur / paused | durée dernière passe, marchés scannés, raisons | Relancer manuellement |
| OpenAI | configurée / dernière requête OK / coût / quota / erreur | dernier appel réel, modèle, durée, expiration | Probe explicite seulement |
| RSS / calendrier | OK / exp expiré / indispo | source, collecte, droits | Rafraîchir contrôlé |
| SQLite / Paper | ready / dirty / sauvegarde requise / erreur | version schéma, transaction, checkpoints | Sauvegarder / restaurer après confirmation |
| Workers Qt | prêt / en cours / bloqué / erreur | job, âge, taille file et erreur | Diagnostiquer |

Un simple « CONNECTÉ » doit toujours être interprétable. Le bandeau supérieur n'affiche qu'un résumé et ouvre ce panneau détaillé par clic.

### Politique de health checks

- IG REST : heartbeat **espacé**, non bloquant, conforme quotas et état de session; renouvellement de jetons piloté par adaptateur; backoff exponentiel borné et jitter sur erreurs persistantes.
- IG Streaming : événements de connexion et âge des derniers messages, distinction marché fermé et panne; un flux inactif pendant fermeture marché ne signifie pas automatiquement défaillance sans calendrier.
- IA : pas de ping payant automatique ; statut *configuration disponible / dernière requête / expiration* ; contrôle manuel de bout en bout sur demande.
- Journal : code erreur, correlation_id, instant UTC, nom de la source, impact, remédiation, redaction; ne jamais logger mots de passe, clés ou tokens.
- Afficher le dernier succès réel plutôt que l'instant du dernier rafraîchissement d'UI.

## B. Paramètres

Sous-onglets `Connexions`, `Marchés`, `Stratégies`, `Risques`, `IA`, `Notifications`, `Interface`, `Avancé`.

**Connexions** : DEMO/LIVE, profil et compte, keyring, source des cotations; secrets masqués.
**Marchés** : références surveillées, budget streaming, famille/EPIC bindings contrôlés, timeframes.
**Stratégies** : indicateurs, paramètres, pondérations et seuils; avertir si profil preview non qualifié pour AUTO.
**Risque** : 1 % par trade / 3 % journalier proposés, plafonds positions par marché/global et corrélation, break-even +1R paramétrable, mode exécution et kill switch existant; droits persistants sans activation réelle implicite.
**IA** : provider, modèle, périmètre, consentement, fréquence, TTL, budget, désactivation, envoi des données historiques.
**Notifications** : canaux, gravité, cooldown, test sans trade.
**Interface** : langue FR/EN, thème sombre, taille police, mode compact, format numérique, timezone d'affichage, variation forte on/off/seuils, layout, restaurer défaut.
**Avancé** : diagnostics, export expurgé, réglages versionnés et migration.

Les réglages héritent de la configuration existante. `ConfigMigrator` doit accepter l'ancien `WorkspaceState` largeur/hauteur/splitter et y ajouter optionnellement `layout_version`, `window_geometry`, `main_page`, `tabs`, `panel_visibility`, `locale`, `theme`, sans casser les fichiers existants. Les secrets restent en keyring.

## Exigences

- **GUI2-OPS-001** : états santé IG REST/streaming/market data/IA séparés, vérifiés et horodatés.
- **GUI2-OPS-002** : supervision non bloquante avec backoff, respect quota et distinction marché fermé/flux stale.
- **GUI2-OPS-003** : aucun ping IA payant sans consentement ni action explicite.
- **GUI2-OPS-004** : navigation vers diagnostic détaillé depuis le badge bandeau.
- **GUI2-OPS-005** : configuration de l'interface et langue persistantes; autres paramètres présents mais pas nouveaux droits d'exécution.
- **GUI2-OPS-006** : validation de type, bornes, unités et dépendances des paramètres métier.
- **GUI2-OPS-007** : alertes critiques persistantes et accusé de réception; export journal expurgé.
- **GUI2-OPS-008** : restauration de disposition et migration config backward-compatible.
- **GUI2-OPS-009** : arrêt d'urgence visible uniquement si fonctionnalité effective, sans induire de protection broker non existante.
- **GUI2-OPS-010** : mesures CPU/Qt loops/temps de rendu et erreurs, sans télémétrie externe par défaut.

## Acceptation

Simuler refus de flux IG : badge reste `IG REST connecté` si REST valide mais `Streaming REFUSÉ` et marché `UNAVAILABLE`; aucune erreur masquée. Une clé OpenAI non configurée n'entraîne aucun appel. Changer le thème ou la langue ne modifie pas les montants `Decimal` ni les limites de risque.
