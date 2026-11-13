# Verification

- `pytest` cible fournisseurs, normalisation, quota et scheduler : 12 passes.
- `ruff check` sur les nouveaux modules et tests : vert.
- Aucun transport reseau reel invoque.
# Verification complementaire TIG-INTEL-004/005

- `python -m pytest -q` : **741 passed**.
- Tests cibles Market Intelligence, Macro GUI et credentials : **25 passed**.
- Ruff cible sur les fichiers modifies : **passed**.
- Ruff global : **484 constats preexistants** dans `scripts/codex`, hors
  perimetre de ce lot et non modifies.
- Aucun appel d'ordre IG, aucune activation AUTO et aucune facturation
  automatique pendant la verification.

# Verification fraicheur et stabilite Tavily

- Tests cibles fournisseurs/runtime/GUI : **10 passed**.
- Ruff cible sur les six fichiers modifies : **passed**.
- Suite complete : **743 passed**.
- Aucun appel reseau reel ; transports Tavily mockes dans les tests.

# Verification TIG-INTEL-007 — enrichissement article

- Tests cibles config, fournisseurs, Extract partiel, contenu absent,
  deduplication, selection de cinq sources, circuit breaker/quota, IA, GUI et
  SQLite : **76 passed**.
- Suite complete : **749 passed**.
- `ruff check src/trading_ig_assistant tests` : **passed**.
- Aucun appel reseau reel, ordre IG, activation AUTO ou facturation automatique.
- Test de persistence : faits et URL presents; extrait integral explicitement
  absent des tables SQLite.

# Verification TIG-INTEL-008 — collecte manuelle Tavily

- Une seule requete Search par actualisation manuelle, avec l'horizon maximal
  de sept jours par defaut; aucun surcout de recherche par categorie.
- Test de reclassement : une publication de banque centrale agee de 48 heures
  est conservee par la fenetre 72 heures, tandis qu'une actualite generique du
  meme age est rejetee par la fenetre breaking de 6 heures.
- Test de statut : une reponse sans article exploitable produit
  `TAVILY_EMPTY/UNAVAILABLE`, et non un faux `READY`.
- Tests cibles : **25 passed**. Suite complete : **751 passed**.
- Ruff cible : **passed**. Aucun appel reseau reel ni aucune action IG.

# Verification TIG-INTEL-009 — semantique temporelle Tavily

- Le payload Search utilise `start_date/end_date` pour la date de publication;
  `max_age_hours`, reserve a la fraicheur du cache Tavily, n'est plus envoye.
- `filter_by_published_date=false` preserve les sources sans date detectee;
  elles restent marquees comme date inconnue et soumises aux controles locaux.
- Les erreurs et collectes vides sont distinguees dans le statut GUI Tavily.
- Tests cibles : **19 passed**. Suite complete : **751 passed**.
- Ruff cible : **passed**. Aucun appel Tavily reel pendant les tests.

# Verification TIG-INTEL-006 — lisibilite et indicateurs techniques

- La table des preuves IA affiche des lignes bornees, des infobulles completes
  et un libelle distinct avant/apres analyse.
- Le panneau de resultat n'est plus vide avant le premier appel consultatif.
- Les cases d'indicateurs non produites par la strategie choisie sont desactivees
  et decochees; les valeurs et periodes attestees sont explicitees.
- Test de fondation GUI : hauteur minimale inferieure ou egale a 768 pixels pour
  chaque page chargee paresseusement.
- Tests cibles : **20 passed**. Suite complete : **752 passed**.
- Ruff cible : **passed**. Aucun appel reseau, ordre IG ou activation AUTO.
