# Progress

- [x] Périmètre et sources de vérité relus.
- [x] Impact domaine/service/UI analysé.
- [x] Interruption prioritaire : rendre visible et actionnable un appel IA terminé sans résultat conforme.
- [x] Contrat et calcul de série EMA.
- [x] Projection des bougies Watchlist.
- [x] Courbes graphiques et contrôles.
- [x] Tests ciblés (104 tests) et lint.
- [x] Régression complète.
- [ ] Validation visuelle utilisateur.

## Correctif IA incidentel

- Les deux clics utilisateur ont été confirmés par deux analyses archivées comme indisponibles.
- L'UI distingue désormais « pas encore lancé » de « tentative terminée sans résultat conforme ».
- Les diagnostics fournisseur sûrs sont propagés sans corps de réponse ni identifiant.
- La limite de sortie par défaut passe à 1000 jetons pour le contrat enrichi structuré.
- Un échec d'archivage local ne masque plus un résultat consultatif valide en mémoire.

## Courbes EMA

- Nouveau contrat immuable de série d'indicateur horodatée, avec états READY,
  WARMING_UP et INVALID explicites.
- EMA rapide et lente calculées uniquement sur le suffixe continu des bougies
  clôturées ; la bougie courante est exclue.
- Les périodes viennent exclusivement de la provenance du signal technique.
- Les anciennes lignes EMA horizontales ont été retirées au profit de vraies
  courbes synchronisées avec les axes réel et compressé.
- Les courbes sont recalculées lors d'un changement de résolution ou de base de
  prix et restent indisponibles tant que la période lente n'est pas couverte.

