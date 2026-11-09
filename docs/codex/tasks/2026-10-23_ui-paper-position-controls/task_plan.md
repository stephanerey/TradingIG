# Plan — contrôles locaux des positions Paper

## Objectif

Permettre, depuis le portefeuille Paper volatil, de resserrer explicitement le stop d'une
position ouverte et de la clôturer manuellement, sans aucun chemin d'ordre IG.

## Périmètre

- Exposer les primitives Paper existantes par la session locale.
- Ajouter des actions explicites sur la position sélectionnée.
- Refuser tout élargissement du stop et journaliser confirmations/refus.
- Conserver l'état volatil, sans persistance ni nouvelle dépendance.

## Preuves prévues

- Régressions service long/short, refus d'élargissement et clôture manuelle.
- Régression GUI de bout en bout strictement locale.
- Suite hors ligne complète et tests protégeant les méthodes d'ordre IG.
- Smoke Qt 960×600 du portefeuille Paper.

## Skills

- `codex-tradingig-paper-execution`

