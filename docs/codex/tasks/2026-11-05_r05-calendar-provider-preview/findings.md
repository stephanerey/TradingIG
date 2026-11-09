# Findings

## FRED — Federal Reserve Bank of St. Louis

- API JSON/XML officielle et documentée, clé gratuite obligatoire.
- `fred/releases/dates` peut inclure les dates futures avec
  `include_release_dates_with_no_data=true`.
- La réponse structurée documentée contient date, ID et nom de publication, mais pas l'heure ni une
  importance calibrée ; elle est donc insuffisante seule pour un veto intrajournalier précis.
- Sources : <https://fred.stlouisfed.org/docs/api/fred/releases_dates.html> et
  <https://fred.stlouisfed.org/docs/api/api_key.html>.

## BLS — calendrier iCalendar officiel

- Le BLS publie `https://www.bls.gov/schedule/news_release/bls.ics`, automatiquement mis à jour,
  avec les heures des principales publications américaines.
- Un probe antérieur du projet a reçu une page Access Denied ; aucun contournement anti-bot n'est
  autorisé.
- Source : <https://www.bls.gov/schedule/news_release/jolts.htm>.

## Eurostat

- Calendrier officiel public en heure Europe/Luxembourg, notamment pour inflation, PIB, emploi et
  indicateurs européens.
- La recherche officielle n'a pas identifié de contrat JSON/iCalendar stable pour le calendrier ;
  l'API SDMX concerne les données publiées, pas l'horaire structuré des annonces.
- Source : <https://ec.europa.eu/eurostat/news/release-calendar>.

## Trading Economics

- API calendrier structurée avec heure UTC, ID, pays, catégorie, source/source URL,
  `DateSpan` et importance 1–3 ; correspond directement au contrat TradingIG.
- Nécessite un abonnement et une clé ; l'intégration doit donc être explicitement autorisée et la
  clé rester hors config/repo/logs.
- Sources : <https://docs.tradingeconomics.com/economic_calendar/schema/> et
  <https://docs.tradingeconomics.com/get_started/>.

## Conclusion

- Meilleure couverture automatique : Trading Economics, avec coût et dépendance fournisseur.
- Option officielle gratuite : combinaison FRED/BLS, incomplète et actuellement bloquée pour BLS.
- Option sans réseau : import iCalendar local explicite, fiable mais manuel.

