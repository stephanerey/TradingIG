# Findings

- `PaperBroker` est déjà isolé des adaptateurs IG et conserve positions/événements en mémoire.
- Le ticket GUI sait construire et évaluer un `TicketDraft`, mais n'expose encore aucun chemin
  vers `PaperBroker`.
- `journal_view.py` et `monitor_view.py` sont encore des placeholders ; la fenêtre principale
  n'affiche que l'onglet Produits/Ticket.
- Les hypothèses de fill sont actuellement globales au `PaperBroker`, alors que le ticket GUI
  permet de les saisir par proposition. Elles doivent rester cohérentes lors du fill et de la
  clôture.
- `PaperBroker.process_quote()` clôture correctement stop/objectif/KO, mais le coordinateur doit
  libérer la réservation de risque après une telle clôture.
- Les hypothèses sont désormais attachées à chaque intention : le même modèle de frais/slippage
  est utilisé à l'ouverture, au marquage latent et à la clôture.
- Le journal de session combine la proposition, le résultat et les événements append-only du
  broker sans ouvrir la base SQLite.
- Le smoke Qt conserve 960×600 ; le runner offscreen ne rend pas les glyphes, limitation visuelle
  déjà connue, mais les tables et compteurs sont vérifiés fonctionnellement.

