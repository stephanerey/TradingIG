# Plan — niveaux relatifs/absolus du ticket Paper

## Objectif

Ajouter un mode relatif proche de la saisie IG, prérempli avec une distance stop de 40 et une
distance objectif de 80, tout en conservant un mode absolu explicite.

## Périmètre

- Mode relatif par défaut pour stop et objectif uniquement.
- Conversion déterministe vers des niveaux absolus selon le sens et l'entrée simulée.
- Mode absolu disponible par choix explicite.
- KO Barrière conservé en niveau absolu séparé.
- Résumé affichant le mode et les niveaux résolus avant ouverture Paper.

## Preuves prévues

- Achat et vente relatifs, valeurs par défaut et conversion de mode.
- Compatibilité du mode absolu et maintien des vetoes risque/FX/KO.
- Affichage 960×600 sans débordement horizontal.
- Suite complète hors ligne et protections des méthodes d'ordre IG.

## Skills

- `codex-tradingig-accounts-risk`
- `codex-tradingig-paper-execution`

