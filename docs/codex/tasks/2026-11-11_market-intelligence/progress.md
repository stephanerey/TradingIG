# Progression

- 2026-11-11 : audit des contrats, sources officielles, frontiere Qt et PRD.
- 2026-11-11 : verification des contrats officiels Tavily Search/Pricing et
  GDELT DOC 2.0.
- 2026-11-11 : TIG-INTEL-001 a 003 termines ; 12 tests mockes et lint cible verts.
- 2026-11-11 : TIG-INTEL-004 termine ; orchestration Qt asynchrone, sources
  officielles, Tavily et GDELT raccordees sans capacite d'execution.
- 2026-11-11 : TIG-INTEL-005 termine ; contribution Tavily rendue visible,
  couverture par categorie exposee dans Contexte global et provenance IA
  explicitee. Les metadonnees brutes restent disponibles a la demande.
- 2026-11-11 : la saturation publique GDELT HTTP 429 est classee comme
  limitation temporaire, avec temporisation de 15 minutes au lieu de relances
  agressives. Aucun secret GDELT n'est requis.
- 2026-11-11 : la selection des 20 metadonnees envoyees a l'IA est maintenant
  equilibree entre fournisseurs ; Tavily/GDELT ne peuvent plus etre evinces par
  un volume superieur de publications officielles. Les heures absentes ne sont
  plus presentees comme `00:00`.
- 2026-11-11 : les preuves citees par l'IA sont restituees avec fournisseur,
  titre et source plutot qu'avec les identifiants internes `news:*`. Le bouton
  de metadonnees techniques et les causes d'indisponibilite GDELT sont lisibles.
- 2026-11-11 : l'avertissement d'analyse obsolete compare maintenant l'heure IA
  a l'heure de collecte des actualites, et non a chaque regeneration de la
  projection GUI. Le faux positif observe apres une analyse recente est corrige.
- 2026-11-11 : 741 tests passent. Le lint cible passe ; le lint global reste
  rouge sur 484 infractions preexistantes dans scripts/codex hors lot.
- 2026-11-11 : les resultats Tavily sont maintenant controles localement sur
  leur fenetre de fraicheur, fusionnes et dedupliques entre deux collectes au
  lieu d'etre remplaces en bloc. Les dix resultats recents sont visibles avec
  date et heure UTC completes. La suite compte desormais 743 tests verts.
- 2026-11-11 : TIG-INTEL-007 termine. Tavily Search fournit l'extrait court;
  Extract Basic complete seulement les contenus insuffisants, par lot de cinq,
  apres consentement. La selection combine pertinence, qualite et diversite.
- 2026-11-11 : les fenetres sont configurables par categorie (6h breaking,
  24h macro, 72h politique monetaire, 168h geopolitique par defaut). GDELT
  respecte Retry-After avec circuit breaker et degradation explicite.
- 2026-11-11 : l'interface affiche avant consentement sources, volume, cout
  estime et credits; apres analyse elle montre les extraits utilises et permet
  d'ouvrir les URL d'origine. Aucune donnee sensible IG n'est transmise.
- 2026-11-11 : SQLite v3 conserve analyses, faits, timestamps et references
  append-only. Les extraits complets ne sont jamais ecrits sur disque.
- 2026-11-11 : suite complete **749 tests verts** et Ruff `src/tests` vert.
- 2026-11-11 : correctif TIG-INTEL-008. La collecte manuelle ne classe plus
  toute la recherche Tavily en breaking news sur six heures. Une seule requete
  couvre l'horizon maximal configure, puis chaque article est reclasse
  (macro, politique monetaire, geopolitique, energie ou breaking) avant
  application de sa propre fenetre de fraicheur. Un resultat vide n'est plus
  presente comme `READY`.
- 2026-11-11 : suite complete **751 tests verts** apres le correctif de collecte
  manuelle; Ruff cible vert.
- 2026-11-11 : correctif TIG-INTEL-009. `max_age_hours` etait interprete a
  tort comme l'age de publication alors qu'il borne l'age du cache Tavily.
  La recherche utilise maintenant `start_date/end_date`, garde les resultats
  sans date comme dates inconnues, puis applique les bornes horaires exactes
  localement. La requete manuelle a aussi ete reformulee en langage naturel.
- 2026-11-11 : les causes Tavily sont maintenant explicites dans l'interface
  (aucun resultat recent, reseau, quota, HTTP ou reponse inexploitable).
  Suite complete **751 tests verts**, tests cibles **19 verts**, Ruff vert.
- 2026-11-11 : TIG-INTEL-006 termine. La table des preuves IA distingue la
  preselection des sources des extraits effectivement utilises, borne la hauteur
  de chaque ligne, expose le texte complet en infobulle et conserve un panneau
  de resultat explicite avant le premier appel.
- 2026-11-11 : les controles du graphique ne sont plus affiches comme disponibles
  lorsque la strategie selectionnee ne produit pas la donnee correspondante.
  ATR, RSI, EMA rapide/lente, support et resistance sont listes avec leurs
  periodes attestees; aucune courbe historique n'est inventee.
- 2026-11-11 : la mise en page reste compatible 1366x768. Tests cibles
  **20 verts**, suite complete **752 tests verts**, Ruff cible vert.
