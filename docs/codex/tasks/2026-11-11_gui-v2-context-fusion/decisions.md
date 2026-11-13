# Decisions

- Ne pas ajouter de nouveau topic de souscription UI : le scanner lit le meme
  runtime au moment de l'evaluation, ce qui limite le couplage.
- Ne pas deduire une direction par nom d'instrument ou par EPIC.
- Ne pas rendre l'analyse IA obligatoire : le scanner conserve son fallback
  macro inconnu quand aucun snapshot n'existe.
- Effacer le snapshot quand les actualites changent pour eviter d'associer une
  analyse ancienne a une collecte plus recente.
- Laisser le service domaine gerer les snapshots expires ou hors portee.
