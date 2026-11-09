# Acceptance Matrix — TradingIG V1.2

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstructed from the recovered V1.1.

**Last updated:** 2026-10-22

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 19; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-19"></a>

## 19. Grille de tests d'acceptation de bout en bout

| ID | Scénario | Résultat attendu |
|---|---|---|
| AC-001 | `main` ancien et branche avancée comparées | L'application repart de `512c16d` sur une branche de travail, aucun code fonctionnel perdu |
| AC-002 | Quota historique IG épuisé, cache présent | Le cache local est chargé sans tentative REST répétée |
| AC-003 | Cinq sous-bougies M1 forment un M5 | O/H/L/C et statut clôturé corrects, même en cas d'updates multiples |
| AC-004 | Requête historique lente de 20 s simulées | La GUI continue de recevoir clics et rafraîchissements non bloquants |
| AC-005 | CFD et Barrières d'un même sous-jacent | Les deux comptes sont affichés, exposition regroupée, plafond marché partagé |
| AC-006 | Changement de compte refusé | Aucun ordre/signal d'exécution dirigé vers le mauvais compte |
| AC-007 | P&L journalier atteint -3 % | Plus de nouvelles ouvertures ; gestion des positions toujours active |
| AC-008 | Position globale existante, plafond 1 | Deuxième ordre pending/exécuté refusé, y compris en concurrence |
| AC-009 | Analyse technique 80/100, sentiment IA opposé | Score et divergence expliqués ; le Risk Engine peut bloquer séparément |
| AC-010 | Indicateur sans warmup suffisant | `WARMING_UP`, aucune décision exécutable |
| AC-011 | Profit atteint +1R | Stop net proposé avec frais, sans garantie d'exécution ; statut protégé après confirmation broker |
| AC-012 | Broker refuse l'update stop | Position ne passe pas `PROTECTED`, alerte et audit |
| AC-013 | Réponse ordre timeout | `UNKNOWN`, réconciliation avant toute nouvelle commande ; zéro renvoi aveugle |
| AC-014 | Mode `ANALYSIS` et clic « Trader » | Aucun appel HTTP d'ordre ; éventuelle proposition paper séparée |
| AC-015 | Fermeture GUI avec pending logiciel | Avertissement et indication de perte de protection si arrêté |
| AC-016 | Notification SMTP/Telegram échec | Événement d'alerte reste visible localement ; aucune influence sur Risk Engine |
| AC-017 | Historique journal importé | Statistiques jour/semaine/mois concordantes nettes de frais, pas de doublons |
| AC-018 | Stratégie testée sur données futures | Test temporel détecte ou interdit une fuite de données dans le replay |
| AC-019 | LLM produit un ordre non conforme | Rejet déterministe indépendant du commentaire IA |
| AC-020 | API KO Barrières non supportée | Capacité `UNSUPPORTED`, route d'ordre désactivée, explication utilisateur |
| AC-SR-001..006 | SR00 version publiée, préservation des personnalisations et post-check | Source SR 4.1.0 vérifiée ; aucune modification du code métier ; validation humaine séparée |
