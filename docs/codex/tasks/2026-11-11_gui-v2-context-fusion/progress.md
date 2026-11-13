# Progression

- 2026-11-11 : audit du runtime, du controleur Macro/IA, du scanner et du
  service de projection produit existant.
- 2026-11-11 : le runtime conserve desormais le snapshot domaine avec rejet
  des generations obsoletes et remise a zero lors d'une nouvelle generation.
- 2026-11-11 : le controleur Macro/IA publie le contexte atteste et l'invalide
  des qu'une nouvelle collecte rend l'analyse precedente obsolete.
- 2026-11-11 : le scanner consomme le contexte reel au lieu de fabriquer
  systematiquement un ruban macro `UNKNOWN`; le fallback inconnu est preserve.
- 2026-11-11 : le contexte explicable est projete dans le scanner et la
  watchlist avec niveau, composantes, raisons, provenance et veto de securite.
- 2026-11-11 : le ruban compact du shell distingue couverture d'actualites,
  contexte IA frais et absence de preuve, sans appeler de service payant.
- 2026-11-11 : lot clos apres lint cible, 22 tests cibles et 756 tests globaux.
