# Plan SR — Market Intelligence

Skills appliques : `aurora-architecture-check`, `aurora-lot-runner`,
`codex-tradingig-analysis-scanner` et `aurora-to-prd` pour conserver les
frontieres domaine/adaptateurs/services/GUI existantes.

1. Introduire des contrats immuables, UTC et non directionnels.
2. Implementer Tavily Basic et GDELT DOC avec transports injectables.
3. Ajouter quota persistant, deduplication et decisions de scheduler pures.
4. Raccorder les sources officielles, l'analyse consultative et la projection GUI.
5. Verifier par tests mockes, lint cible puis suite complete.
6. Enrichir au plus cinq articles apres consentement : extrait Tavily Search,
   puis Tavily Extract Basic par lot de cinq seulement si necessaire.
7. Conserver les extraits uniquement en memoire et persister les faits structures,
   les sources et les references d'analyse dans SQLite append-only.

Les lots ne modifient ni les ordres IG, ni le mode LIVE, ni l'automatisation du
trading. Aucun secret n'est stocke dans le depot.

TIG-INTEL-007 n'envoie aucune donnee IG sensible. Il affiche avant consentement
le volume, le cout OpenAI estime et le credit Tavily Extract maximal, puis rend
lisibles les extraits reellement utilises et leurs liens.
