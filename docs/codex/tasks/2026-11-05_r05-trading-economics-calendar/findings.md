# Findings

- L'authentification par en-tête `Authorization: <api_key>` est documentée officiellement.
- Le calendrier fournit `CalendarId`, `Date` UTC, `Country`, `Category`, `Event`, `Source`,
  `SourceURL`, `DateSpan`, `Importance` et `LastUpdate`.
- `DateSpan=0` signifie heure connue ; `DateSpan=1` signifie horaire estimé.
- Le contrat projet `EconomicCalendarProvider` existe déjà et retourne des `MacroEvent`.
- Les droits du futur abonnement ne sont pas encore vérifiés : ils doivent être injectés
  explicitement et rester `UNKNOWN` par défaut.

