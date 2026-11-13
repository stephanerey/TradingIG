# Decisions

- Architecture additive ; aucune extension du moteur d'execution.
- Metadonnees seulement : titre, URL, dates, classifications et provenance.
- GDELT est non confirme par defaut ; la corroboration vient de sources
  distinctes, jamais de la tonalite.
- Le plafond Tavily applicatif est independant du forfait fournisseur.
- Une collecte manuelle conserve jusqu'a dix resultats Tavily recents sur une
  fenetre glissante de six heures ; un nouvel appel fusionne et deduplique au
  lieu d'effacer les resultats encore frais.
- La collecte de contenu n'est pas activee dans ce correctif. Elle sera traitee
  comme un lot d'enrichissement separe avec selection, droits, quotas, taille de
  prompt et consentement explicites.
