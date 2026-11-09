# Décisions

- Le proxy utilise uniquement `MacroRibbonState.event_risk` déjà normalisé.
- `regime` et les biais directionnels ne sont pas transformés en risque : ils restent dans le
  composant Contexte.
- La provenance du ruban et son horodatage sont conservés dans le composant Scanner.
- Un catalyseur favorable peut coexister avec un risque rouge ou jaune.
