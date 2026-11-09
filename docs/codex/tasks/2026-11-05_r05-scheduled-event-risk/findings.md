# Findings

- `MacroEvent`, `MarketContextFlag`, la validation de lignée et l'agrégateur `EventRisk` existent.
- Aucun service ne transforme encore un calendrier structuré en drapeau temporel.
- Le PRD exige qu'un événement à fort impact dans la fenêtre configurée lève un risque, mais ne
  définit pas de seuil temporel par défaut : les fenêtres resteront obligatoirement explicites.
- Aucun fournisseur calendrier réel n'est requis pour ce lot hors ligne.

