# Decisions

- Une preuve news IA porte le tag réservé `ai_evidence`, reste `GRAY`, sans score ni confiance.
- `ai_evidence` peut être citée par le fournisseur IA si elle est valide, mais ne participe jamais
  aux agrégats déterministes du `MacroContextService`.
- L'appel runtime est déclenché uniquement par l'action Outils et après un probe Settings réussi
  dans la même session.
- L'état consultatif est visible dans le ruban, séparé des indicateurs déterministes.
- La durée de validité existante s'applique depuis la collecte effective de chaque fournisseur,
  sans renouvellement par une source tierce et sans durée de pertinence arbitraire pour un titre.
- Les évaluations et catalyseurs utilisent une borne de fin exclusive ; une analyse relative à un
  autre produit ou expirée reste grise. Le minuteur Qt est une mise à jour locale de présentation,
  sans requête ni activation de trading.
