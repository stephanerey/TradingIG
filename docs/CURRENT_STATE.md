# CURRENT_STATE.md — TradingIG

## Dernière mise à jour
- Date : 2026-11-06
- Auteur : Codex / humain

## Résumé court
Application desktop PyQt5 existante, conservée et reprise sans reconstruction. SR Method 4.1 est installé et vérifié. R00–R07 et les lots GUI Paper sont terminés avec preuves locales. Une proposition validée peut ouvrir une position dans une session Paper strictement locale, avec vues Positions/Ordres/Journal, suivi du P&L estimé, resserrement manuel du stop et clôture locale explicite. Deux actions explicites permettent de sauvegarder ou restaurer le dernier checkpoint local append-only et contrôlé par checksum ; aucune base n'est ouverte au démarrage. Le ticket propose par défaut des distances relatives stop/objectif `4/12`, cohérentes avec le profil initial equity 1 000 EUR/risque 1 %/taille 1, avec un mode absolu alternatif ; le KO Barrière reste absolu et sa perte max initiale de 9 EUR est une hypothèse Paper à vérifier. Le test R07 DEMO borné a confirmé une ouverture CFD minimale, un resserrement de stop et une clôture avec zéro position finale. R05 dispose de frontières typées pour macro/news et IA ainsi que de sources automatisées Fed/BCE en lecture seule. Le probe GUI OpenAI a été validé humainement avec `gpt-6-luna`. Après ce probe, une action manuelle ou un consentement distinct de session peut envoyer au modèle jusqu'à 20 titres officiels autorisés, sous forme de preuves grises sans score, puis afficher une analyse consultative séparée dans le ruban. Le consentement périodique, désactivé et non persisté par défaut, déclenche au plus un appel toutes les 15 minutes et le résultat ne touche ni scanner, ni ticket, ni ordre. R08 dispose d'un gate AUTO default-deny, de métriques replay, d'un flux future-blind, d'un orchestrateur de signaux et de plans chronologiques/walk-forward liés à l'empreinte du dataset, purement hors ligne et sans chemin broker. La GUI V2 propose désormais DEMO ou LIVE en lecture seule et affiche partout le mode Simulation ; les contrats internes historiques restent nommés PAPER pour compatibilité. AUTO et toute exécution broker LIVE restent désactivés.

## Stack détectée
- Python : 3.12.6 dans `.venv` projet (`pyproject.toml` exige >=3.11)
- Layout : `src/trading_ig_assistant`
- UI : PyQt5 + pyqtgraph
- Tests : pytest
- Packaging : `pyproject.toml` / setuptools

## Dernière tranche terminée
- SR00, R00–R07, le ticket GUI, la session/les vues Paper et les cœurs génériques replay R08-2/5
  sont terminés localement, sans commit.

## Tranche active
- Le moteur technique écrit désormais chaque évaluation de stratégie et chaque échec explicite
  dans le journal SQLite append-only existant, avec bougies closes, indicateurs, niveaux,
  décisions et provenance. Le compte IG est pseudonymisé dans la base. Une commande dédiée
  exporte un paquet de validation encore plus strict, sans identifiant de compte, PnL, ticket,
  ordre ni position, pour dépôt manuel dans Rooms. Cet ajout est purement observationnel : il
  ne modifie aucun signal et n'ouvre aucun chemin d'exécution IG.
  La régression complète associée passe avec 776 tests ; une session GUI déjà ouverte doit être
  relancée avant de produire ses premiers événements exportables.
- Le bandeau GUI V2 regroupe maintenant à gauche le choix DEMO/LIVE et une action unique de
  connexion : PLAY bleu avant connexion, STOP vert lorsque la session read-only est active.
  L'action STOP permet la déconnexion et le sélecteur d'environnement reste alors verrouillé.
  À droite, Equity IG, Solde, Disponible et PnL IG sont affichés dans quatre cartes à chiffres
  agrandis; seul le PnL attesté utilise le vert/rouge financier. Les rafraîchissements temps réel
  ne reconstruisent plus le menu des comptes, supprimant son scintillement. Les noms et types
  broker, y compris SPREAD BET/ACTIONS ou un type brut inconnu, rendent tout compte supplémentaire
  identifiable. Les captures Qt natives sont lisibles et la suite complète passe avec 693 tests.
- Dans la liste des produits, une analyse IA du marché de référence peut être affichée pour un
  produit uniquement si son EPIC exact possède un binding explicite vers cet EPIC de référence.
  La mention « référence » et la provenance du binding sont visibles ; les dates, périmètres et
  risques restent contrôlés. Aucun binding n'est deviné et ce raccordement de présentation ne
  modifie pas le périmètre du Scanner ou l'exécution. Les EPIC DEMO `IX.D.CAC.OPTCALL.IP` et
  `IX.D.CAC.OPTPUT.IP` vus le 2026-11-06 ne sont pas les EPIC LIVE `...2.IP` configurés : ils
  restent non liés tant qu'une preuve explicite n'est pas obtenue. Validation Windows à grouper.
- La liste affiche désormais l'exposition haussière/baissière lorsque le nom d'une Barrière
  se termine explicitement par « Barrière(s) Achat/Vente ». Cette indication est déduite du nom,
  sans modification du modèle produit ou du sens du ticket ; le contexte utilisait déjà les mêmes
  mots. Le sens d'exposition et celui d'un ordre restent distincts. La logique préexistante du
  ticket reliant certains `ProductDirection` au sens d'ordre a été supprimée : au changement de
  produit, le ticket Paper propose Achat indépendamment de l'exposition et laisse le choix manuel.
  Un rafraîchissement du même produit préserve ce choix. Aucune capacité d'exécution IG n'est
  déduite de ce comportement Paper ; les dérivés restent non qualifiés pour exécution.
- Recherche IG ciblée manuelle depuis le filtre : une requête de recherche en lecture seule,
  aucun appel de détails par produit, ajout dédupliqué en mémoire pour la session seulement et
  refus du résultat si la connexion, le compte ou la génération du flux a changé. Les résultats
  temporaires sont retirés lors de l'invalidation de connexion ; aucun cache n'est réécrit. Cette
  recherche vise à investiguer les dérivés DEMO, sans prouver leur disponibilité ni leur capacité
  d'exécution. Validation humaine DEMO du 2026-11-06 : la recherche « France 40 » a fait passer
  la liste de 565 à 567 produits et montré deux produits nommés Barrières Achat/Vente. Leur statut
  et leur capacité de négociation DEMO n'ont pas été vérifiés par cette seule capture.
- La découverte DEMO en cache du 2026-11-06 contient 565 produits issus des catégories : 551
  CFD/actions, 14 inconnus et aucun dérivé reconnu. Trois ETF/ETP `SHARES` étaient classés à tort
  comme options à cause de leur nom ; la classification privilégie désormais le type IG exact,
  y compris à la lecture des anciens rapports sans les réécrire. Le cache LIVE contient toujours
  58 barrières et 599 options. Ces données ne prouvent pas l'indisponibilité des dérivés en DEMO :
  les chemins de découverte et les droits du compte peuvent différer.
- Recherche web OpenAI consultative manuelle : action Tools distincte, produit sélectionné,
  résultat en français avec liens HTTPS cités ; aucune transmission de compte ou d'ordre. Recherche
  et citations absentes ou réponse incomplète rendent le résultat indisponible. Les sources web
  sont reprises comme une synthèse secondaire, non vérifiée indépendamment, dans un
  `MarketContextSnapshot` consultatif pour le produit et le ruban ; aucun ordre n'est créé.
  Un test réel `gpt-6-luna` a produit une synthèse et six sources ; un premier essai
  avait retourné une réponse incomplète. L'utilisateur a confirmé sous Windows l'affichage de
  la recherche et du ruban AI sur France 40.
- Correction de la recherche web : un essai France 40 a reproduit `max_output_tokens`, avec
  réponse incomplète. Plafond porté à 6 000 tokens, raisonnement réduit pour GPT-6 et diagnostics
  distincts sans secrets ; test réel dans le worker Qt réussi avec sources affichées. La cause
  exacte de l'échec signalé par l'utilisateur n'était pas journalisée et reste donc non prouvée.
- Le résultat de la recherche déclenche une seconde analyse OpenAI explicitement annoncée dans
  la fenêtre ; le snapshot source expire après dix minutes et son périmètre est le produit choisi.
  En cas d'échec de l'analyse, une erreur est affichée et la recherche demeure consultable.
  Test réel Qt/OpenAI et affichage Windows validés. Cela n'établit pas
  que les actualités, leurs citations, leur interprétation ou le sentiment sont exacts.
- R08 est active hors ligne : gate AUTO default-deny, métriques replay, flux future-blind,
  orchestration signal-only et planification train/validation/test/walk-forward implémentés, sans
  activation ni liaison à l'exécution. Les capacités
  Barrières/Options/working orders, AUTO et exécution broker LIVE restent explicitement non
  supportés ; la connexion LIVE read-only n'accorde aucune capacité de mutation.
- R05-AI3 est validé humainement depuis le 2026-11-05 : le contexte consultatif Fed/BCE a été
  accepté avec `openai-responses:gpt-6-luna` et affiché séparément en état `unknown`, sans ticket ni
  ordre. Le contrat borne les citations aux IDs de sources exacts et expose un diagnostic sûr
  `AI_*` en cas de dégradation.
- R05-AI4 ajoute un consentement séparé, explicite et non persisté pour un rafraîchissement OpenAI
  toutes les 15 minutes après probe réussi. Le premier appel réel attend un intervalle complet ; un
  cycle sans preuve officielle ou pendant un appel actif est ignoré. Seuls le contexte normalisé et
  l'epic courant sont transmis. Compte, positions, ticket et ordre restent exclus.
- Les preuves news et la santé Fed/BCE expirent désormais à partir de leur collecte effective ; une
  reconstruction due au calendrier ne prolonge plus artificiellement une ancienne collecte. Les
  preuves futures/expirées sont exclues de l'appel IA, qui est ignoré sans preuve news active ;
  le contexte macro est recalculé au moment de la demande. Aucun nouvel appel réseau ni règle de
  durée de pertinence des titres n'a été ajouté. Au début d'un refresh Fed/BCE, le ruban recalcule
  aussi l'état des anciennes collectes avant toute attente réseau ; validation Windows groupée à
  effectuer.
- Les projections produit et le Scanner réévaluent les signaux macro périmés avant calcul. Une
  analyse IA future, expirée ou relative à un autre produit reste grise ; le ruban expire désormais
  localement le résultat et indique sa portée, sans déclencher d'appel OpenAI. Les bornes des
  catalyseurs expirés sont également exclusives. Tests hors ligne verts, validation GUI groupée à
  effectuer après redémarrage.
- R05-CTX2 projette désormais les événements macro normalisés explicitement `HIGH` en risque
  événementiel rouge dans des fenêtres pré/post obligatoirement fournies, avec lignée et droits
  conservés. Le fournisseur Trading Economics a été choisi et son adaptateur strict est validé
  hors ligne. Son onglet Settings, son probe/refresh non bloquant et sa composition avec les news
  sont implémentés ; `TRADING_ECONOMICS_API_KEY` est absente, donc le test réseau humain reste à
  faire. L'utilisateur a différé cette validation jusqu'à un éventuel abonnement.
- Le catalogue d'indicateurs R05 couvre désormais SMA, EMA, RSI, ATR, MACD, Bollinger,
  momentum/ROC, niveaux récents, volatilité réalisée et ratio de volume fourni. Les sorties
  multi-valeurs, paramètres, warmup/invalidité et provenance sont explicites.
- La Watchlist GUI V2 projette les EMA du signal sur le prix et propose un unique sous-graphe
  synchronisé `Aucun/RSI/ATR/MACD`, calculé uniquement sur la suite continue de bougies clôturées.
  MACD n'apparaît que si le signal atteste explicitement ses trois périodes ; aucune valeur par
  défaut n'est inventée. Le premier affichage privilégie un signal READY directionnel, le choix
  reste synchronisé avec la table technique et est mémorisé par marché et stratégie pendant la
  session, y compris lorsque le signal est réémis à la bougie suivante. Ce choix ne modifie ni
  signal, ni recommandation, ni ordre.
- L'onglet `Macro / IA > Analyses IA` sépare les extraits utilisés et le résultat dans deux zones
  verticales redimensionnables, sans changer le consentement explicite ni les données transmises.
- `TREND_FOLLOW`, `BREAKOUT` et `PULLBACK` sont implémentées comme moteurs techniques
  configurables sans défaut runtime : BUY/SELL/FLAT, niveaux ATR, exclusions, configuration
  complète et replay future-blind sont audités. `EVENT_DRIVEN` exige désormais événement HIGH à
  droits connus, contexte directionnel lié et réaction prix post-événement ; sinon elle reste FLAT.
- Un onglet `Scanner` provisoire analyse manuellement les trois stratégies techniques sur le
  préfixe de bougies clôturées, en excluant toujours la dernière bougie du graphique. Il affiche
  side/état/raisons/niveaux/validité, sans score partiel ni action de ticket/ordre. Validation
  visuelle Windows et acceptation des paramètres preview restent attendues. Depuis la décision
  humaine du 2026-11-05, le runtime GUI est temporairement `session-only` : aucun snapshot REST ni
  cache de bougies persistant n'est lu, et aucun rattrapage historique n'est tenté. Le flux souscrit
  toujours M1, conserve les observations de la session en mémoire pour BID/MID/ASK et reconstruit
  M5/M15/M30/H1 localement. Les révisions d'une même minute remplacent la version précédente ; un
  ancien intervalle incomplet est exclu. L'absence ou l'insuffisance de bougies reste explicitement
  `WARMING_UP`/dégradée sans bloquer le Paper indépendant. Le contexte macro/sentiment et l'IA
  restent consultatifs et ne remplacent pas les indicateurs déterministes.
- La découverte Barrières/Options projette maintenant, pour chaque ligne, un contexte agrégé
  directionnel (`index`/`gold`/régime), événementiel et IA applicable. L'état est relatif au sens
  du produit, traçable dans une infobulle et explicitement `INCONNU` si les entrées manquent. Ce
  libellé n'est ni une probabilité, ni un score de setup, ni une recommandation et n'ouvre aucun
  chemin ticket/ordre. Le même drapeau est affiché séparément sur les lignes du Scanner de
  l'instrument courant. Le score Scanner pondéré PRD reste à intégrer séparément.
  Le barème contexte validé le 2026-11-05 est : `CATALYSEUR=100` (vert foncé), `ALIGNÉ=75`
  (vert clair), `PRUDENCE=50` (jaune), `DÉFAVORABLE=0` (rouge), `INCONNU=indisponible`
  (gris). `CATALYSEUR` requiert un signal `EVENT_DRIVEN` qualifié, frais, concordant et confirmé
  par le prix ; le runtime ne le fabrique pas tant que ces preuves ne sont pas disponibles.
  La même échelle ordinale et la même palette sont désormais le contrat commun des six composantes
  Scanner. Les évaluateurs déterministes technique, R/R, coûts, qualité des données et risque
  marché sont codés selon les seuils validés, avec vetos et provenance. Le Scanner affiche les
  composantes actuellement calculables par stratégie et laisse le score total `INDISPONIBLE` tant
  que le risque marché complet ou les coûts manquent. Settings expose désormais quatre frais
  estimés globaux, par unité et par côté (`CFD/DFB`, `Barrière`, `Option`, `Inconnu`). Au premier
  affichage, un profil indicatif IG France daté du 2026-11-05 propose `0/0,1/0,1/vide` : zéro pour
  les CFD/DFB hors actions dont le spread est traité séparément, puis 0,1 unité de devise par côté
  pour Barrières et Options. Les champs restent modifiables/effaçables et un bouton restaure ce
  profil. Les CFD actions restent indisponibles car leurs commissions en pourcentage/minimum ne
  rentrent pas dans le modèle forfaitaire. Le composant coûts utilise le spread de
  session plus deux côtés de frais uniquement lorsque le produit coté et la source des niveaux
  techniques ont le même epic. Une barrière/option analysée via son sous-jacent reste donc grise
  plutôt que de comparer deux échelles de prix incompatibles. Le risque marché du Scanner consomme
  désormais le proxy événementiel normalisé du ruban : `HIGH=0` avec veto, `MEDIUM=50`, `LOW=75`
  et `UNKNOWN=indisponible`. Il reste indépendant du contexte directionnel : un catalyseur positif
  ne devient pas silencieusement un marché sans risque. Le niveau 100 n'est pas produit sans preuve
  dédiée de faible risque. Settings expose également les six poids globaux PRD
  (`30/15/20/15/10/10`) et les seuils globaux `Candidate=75`, `Watch=60`, `Reject<60`. Ils sont
  persistés et réellement consommés par le Scanner ; une composante inconnue conserve `NO_TRADE`,
  même si son poids est nul. Un score total reste indisponible si le risque ou les coûts sont
  inconnus.
- Un orchestrateur Scanner multi-marchés, sans dépendance Qt ni broker, accepte désormais plusieurs
  produits/séries/contextes, évalue chaque marché indépendamment, conserve tous les résultats par
  stratégie et produit un classement déterministe global. Un marché périmé ou invalide devient un
  échec local explicite sans masquer les marchés valides. Ce cœur n'est pas encore branché à la
  table GUI provisoire, conformément au report de la refonte visuelle.
- Le registre runtime n'est plus figé : chaque entrée du Scanner multi-marchés peut recevoir un
  profil de stratégies versionné, activer un sous-ensemble de `TREND_FOLLOW`, `BREAKOUT` et
  `PULLBACK`, et injecter leurs configurations déterministes complètes. Le profil par défaut
  reproduit les paramètres preview actuels et reste explicitement non validé pour AUTO.
- Les paramètres de ce profil peuvent maintenant être résolus, feuille par feuille, selon
  `global -> compte -> stratégie -> marché`. La source finale de chaque valeur est inspectable et
  une combinaison invalide est refusée atomiquement. Les patches sont maintenant persistés sans
  secret avec des valeurs typées et les clés validées : ID de compte IG, `StrategyId` et
  sous-jacent canonique. Leur rechargement et leur préservation lors d'un passage par Settings
  sont couverts. Le pont vers `InstrumentMappingRegistry` utilise exclusivement son
  `underlying_id` explicite et refuse un produit non mappé ; la GUI d'édition et l'alimentation du
  registre runtime restent à brancher.
- Le vocabulaire initial des sous-jacents Scanner est fermé et typé : `US_TECH_100`, `FRANCE_40`,
  `GERMANY_40`, `SPOT_GOLD`, `US_CRUDE`. Un alias, nom d'affichage ou EPIC ne peut pas être traité
  comme un sous-jacent canonique ; un mapping inconnu échoue explicitement.
- Le modèle de filiation produit suit désormais la navigation IG validée par l'utilisateur : un
  catalogue paresseux charge une seule page à la fois, conserve le fil d'Ariane exact des node IDs
  IG et ne parcourt pas tout l'arbre au démarrage. Sur le profil DEMO validé le 2026-11-05, les deux
  variantes de `marketnavigation` renvoient toutefois 404 ; le chemin réellement disponible est
  `/categories` puis `/categories/{code}/instruments`. Son schéma `{code, nonTradeable}` est
  désormais supporté et un second catalogue paresseux valide catégorie, `underlyingName` et EPIC
  de référence exacts. Les cinq références attendues ont été observées TRADEABLE en lecture seule.
  Aucun lien public dérivé→sous-jacent n'a été exposé : l'EPIC du produit reste donc distinct et
  son rattachement doit être explicite. Le runtime graphique ne classe plus les produits par nom
  et ne lance plus de recherche de marché pour deviner ce lien : il privilégie une clé d'override
  égale à l'EPIC exact du produit, puis reste sur l'EPIC sélectionné si le mapping manque. Les
  Barrières Achat/Vente US Tech, France 40, Allemagne 40 et Pétrole US observées disposent désormais
  d'un mapping exact vers leur référence validée ; les anciennes clés de configuration par nom
  restent seulement lisibles pour compatibilité. Un chemin absent ou ambigu échoue sans heuristique.
- Le batch Scanner multi-marchés accepte désormais, par marché, un profil résolu distinct pour
  chacune des stratégies techniques. Il évalue les profils sur les mêmes bougies clôturées,
  conserve leur provenance feuille par feuille, fusionne tous les signaux avant de reconstruire le
  consensus et refuse les sélections vides, dupliquées ou `EVENT_DRIVEN` dans ce moteur technique.
- Une frontière de préparation sans Qt joint maintenant un produit à sa série de session uniquement
  via un binding exact `EPIC produit -> sous-jacent canonique -> EPIC de référence`, avec provenance
  obligatoire. Elle projette le contexte, résout les profils compte/stratégie/marché puis construit
  l'entrée du Scanner multi-marchés. Un produit non mappé, une série d'un autre produit ou un EPIC
  de référence divergent sont refusés ; aucun nom ou motif d'EPIC n'est interprété. Cette frontière
  ne lance ni abonnement, ni analyse périodique, ni ticket, ni ordre.
- Un registre multi-marchés de bougies de session route également chaque update M1 vers tous les
  produits explicitement liés au même EPIC de référence. Il réutilise l'agrégation conservative
  M1→M5/M15/M30/H1, applique les révisions par timestamp et isole environnement, compte et EPIC.
  Une référence hors de l'univers explicite échoue ; les cinq références initiales approuvées
  peuvent s'accumuler avant qu'un produit leur soit lié. Ce service reste en mémoire uniquement :
  aucun historique REST ni cache persistant n'est lu ou écrit.
- L'adaptateur Lightstreamer sait maintenant regrouper plusieurs EPIC de référence dans une seule
  souscription graphique M1. Les doublons sont retirés, une souscription identique n'est pas
  recréée et chaque update est rattaché à l'item `CHART` exact ; une identité inattendue est rejetée
  avant d'atteindre les séries. Le runtime Qt branche désormais les cinq références initiales et
  ajoute en tête la source exacte du produit sélectionné si elle diffère, avec un plafond de six.
  Les flux de fond alimentent seulement les séries Scanner de session ; le graphique continue de
  rendre exclusivement la source sélectionnée.
  Le 2026-11-05, l'utilisateur a validé le fonctionnement DEMO et les journaux ont confirmé une
  session LIVE en lecture seule recevant les cinq références. Une reconnexion LIVE six secondes
  après fermeture a ensuite reçu de nouveaux tokens au login mais IG a rejeté le `GET /accounts`
  avec `client-token-invalid`; aucun retry automatique d'authentification n'a été ajouté.
  Une reconnexion LIVE ultérieure a authentifié le compte mais IG a refusé la souscription groupée
  avec `Insufficient permissions`. Le runtime effectue désormais un unique repli sur le graphique
  sélectionné : ses bougies peuvent continuer, tandis que le Scanner multi-marchés est signalé
  dégradé sans boucle de retry ni exploration d'autres marchés. Le 2026-11-06, l'utilisateur a
  relancé la connexion LIVE et les journaux ont confirmé la réception continue des bougies M1 de
  la source sélectionnée après ce repli ; aucun ordre n'a été tenté.
- Le repli d'un groupe CHART est limité à une erreur de permissions de ce groupe : une erreur PRICE
  ou une erreur d'un groupe de taille différente ne réinitialise plus les flux Scanner. Cette
  correction est couverte hors ligne et ne modifie pas la session DEMO actuellement ouverte.
- Le 2026-11-10, la GUI V2 a reproduit en LIVE Barrières/Options le refus
  `CHART:5-markets:1MINUTE: -1 Insufficient permissions` alors que REST, Lightstreamer et le flux
  `ACCOUNT` étaient actifs. Ce n'est donc pas une panne de connexion générale. La GUI V2 retente
  désormais une seule fois chaque référence CHART dans une souscription isolée : un refus propre à
  un marché le marque indisponible sans couper les autres cotations ni les données de compte. Une
  erreur PRICE demeure bloquante et aucun flux de référence n'est inventé. Ce repli est en lecture
  seule et n'ajoute aucun chemin d'ordre.
  La validation humaine qui a suivi confirme le résultat par marché : US Tech 100
  (`IX.D.NASDAQ.IFD.IP`) et Allemagne 40 (`IX.D.DAX.IFMM.IP`) reçoivent leurs bougies M1 ; France 40
  (`IX.D.CAC.IMF.IP`), Or Spot (`CS.D.CFEGOLD.CEF.IP`) et Pétrole US (`CC.D.CL.UEF.IP`) sont chacun
  refusés par IG avec `Insufficient permissions`. Les données ACCOUNT et les cotations PRICE
  autorisées continuent parallèlement. Ces trois absences ne doivent pas être remplacées par des
  bougies d'un instrument différent sans binding et provenance explicites.
  La validation a également révélé deux défauts de présentation corrigés : les références CHART
  autorisées n'existent pas nécessairement comme produits dans le catalogue LIVE Barrières, donc
  leur dernier Bid/Offer et leur variation sont maintenant projetés directement dans le Scanner
  avec provenance `LIVE_REFERENCE_CHART_QUOTE`. Si IG omet les champs de variation mais fournit
  `DAY_OPEN_MID`, ceux-ci sont calculés à partir du MID courant et de cette ouverture attestée.
  Enfin, toute connexion ou bascule de compte purge les bougies de la page Valeurs suivies : une
  série DEMO antérieure ne peut plus rester affichée sous une étiquette LIVE.
  Une seconde régression observée visuellement est aussi corrigée : la reconstruction du Scanner
  déclenchée par une cotation Catalogue sans rapport ne remet plus à `N/A` le Bid/Offer et la
  variation d'une référence CHART absente du catalogue Barrières. La dernière preuve
  `LIVE_REFERENCE_CHART_QUOTE` reste conservée jusqu'à une nouvelle cotation ou un changement de
  génération/session.
- Le 2026-11-10, la liste « Valeurs suivies » a été découplée des cinq références fixes du Scanner.
  Chaque environnement et compte IG possède désormais sa propre séquence persistée d'EPIC exacts,
  vide au premier usage. L'opérateur ajoute uniquement un produit présent dans le catalogue courant
  et peut le retirer depuis la watchlist ; aucun nom ni EPIC DEMO n'est traduit vers LIVE. Les
  produits suivis sont prioritaires dans le budget PRICE et leurs ticks construisent des bougies M1
  locales isolées par environnement/compte/produit. Ces bougies restent des données d'affichage du
  produit exact et ne sont jamais promues en bougies de référence du Scanner. Un binding explicite
  demeure obligatoire pour projeter une analyse existante ou préparer une simulation, et aucun
  chemin d'ordre IG n'a été ajouté.
- La validation LIVE France 40 du 2026-11-06 a ensuite montré une limite distincte : après le repli
  mono-graphique, IG refuse encore `CHART:IX.D.CAC.IMF.IP:1MINUTE` tout en continuant les cotations
  `PRICE` de la Barrière sélectionnée. Le runtime bascule désormais dans ce cas sur des bougies M1
  de session construites depuis ces cotations directes et affiche un état dégradé. Leur EPIC reste
  celui du produit : elles alimentent le graphique mais ne sont jamais présentées au Scanner comme
  bougies vérifiées du sous-jacent. Après redémarrage, l'utilisateur confirme l'affichage d'une
  bougie et plusieurs bougies successives. Le calcul MID du repli utilise maintenant les extrêmes
  des cotations observées plutôt que des extrêmes BID/ASK non simultanés ; les cotations arrivées
  hors ordre sont ignorées et l'horodatage PRICE IG est lu. Cette correction est testée hors ligne,
  et une session Windows démarrée après correction a reçu des cotations de la Barrière pendant
  environ dix minutes. Cela ne prouve ni l'exhaustivité des ticks ni l'exactitude OHLC face à une
  référence indépendante.
  L'accumulation des cotations de repli est isolée par environnement, compte et produit pour éviter
  de réutiliser une minute d'un autre compte après bascule ; correction vérifiée hors ligne.
  Le flux PRICE de la référence n'avait pas pu être diagnostiqué : la limite de 20 abonnements
  pouvait l'exclure derrière les produits visibles. Un essai de priorité a provoqué un refus
  `PRICE: 21 Invalid group` de la souscription groupée ; il a été annulé. La cause exacte du refus
  et l'accès PRICE de la référence restent à isoler. Après refus du CHART sélectionné, un essai
  PRICE à un seul item, séparé du flux produit, est désormais journalisé sans alimenter le Scanner ;
  il est testé hors ligne. Une session LIVE démarrée par l'utilisateur a reçu `21 Invalid group`
  pour cet essai isolé tandis que les cotations de la Barrière continuaient. La cause exacte et
  l'éventuelle disponibilité d'un autre type de flux ne sont pas établies. Un diagnostic isolé
  `MARKET` a aussi été essayé isolément après redémarrage : IG répond `21 Invalid group`. La
  documentation IG annonce son retrait le 2026-05-08 ; l'essai automatique a été désactivé.
  Le flux `PRICE` de référence demeure non résolu et le Scanner reste dégradé.
  Les références avaient été observées sur un compte CFD DEMO, tandis que le refus concernait le
  compte LIVE Barrières/Options : un écart de droits ou de compte est une hypothèse, pas une cause
  démontrée.
- Validation du 2026-11-06 : le compte CFD DEMO reçoit bien des mises à jour CHART pour
  `IX.D.CAC.IMF.IP`, contrairement à l'essai LIVE Barrières/Options. Ce CFD exact est désormais
  lié à lui-même pour le Scanner ; une capture Windows montre 26 bougies clôturées et trois lignes
  techniques. Contexte, risque et coûts restent inconnus, le score total indisponible. La grande
  mèche à 14:30 apparaît aussi dans les données CHART IG ; son exactitude n'est pas vérifiée. Une
  infobulle précise que le score qualité ne vérifie ni les prix indépendamment ni les valeurs
  aberrantes. Aucun droit ou flux LIVE n'a été modifié.
- Le 2026-11-06, l'utilisateur a signalé des variations douteuses sur des options pétrole. Le
  snapshot local contient déjà les mêmes valeurs `netChange` et `percentageChange` dans les
  champs bruts IG de plusieurs CALL/PUT différents ; la table les retranscrit. Leur signification
  produit/sous-jacent n'est pas établie : ne pas les qualifier de variation propre à l'option sans
  preuve supplémentaire. La table, le détail et l'en-tête du graphique quand sa source est l'option
  affichent désormais cette variation comme indisponible tant qu'elle n'est pas qualifiée ; les
  données brutes restent conservées et un graphique de sous-jacent distinct reste inchangé. Les lignes
  non actualisées peuvent en outre provenir du snapshot conservé.
- Les bindings exacts sont désormais persistés sans secret dans la configuration avec EPIC produit,
  sous-jacent canonique fermé, EPIC de référence et provenance. Les paires Barrières US Tech,
  France 40, Allemagne 40 et Pétrole US constituent les défauts de filiation explicites ; un
  binding ajouté est conservé par Settings. Cette filiation ne garantit pas que le compte IG
  possède l'autorisation `CHART` correspondante. Les deux paires Or indistinguables restent
  volontairement non liées. Une
  valeur canonique inconnue ou un produit dupliqué invalide la configuration au lieu d'être
  normalisé par son nom.
- Le rafraîchissement manuel du Scanner utilise désormais le véritable orchestrateur multi-marchés.
  Il assemble uniquement les produits découverts possédant un binding exact avec leurs bougies de
  session, contexte, profils hérités, spread disponible, frais configurés, poids et seuils. Les
  produits absents, en warmup ou périmés sont isolés ; un produit non lié reste utilisable en Paper
  mais ne reçoit aucun contexte Scanner inventé. L'interface provisoire continue d'afficher le
  détail du produit sélectionné ; la liste classée multi-marchés sera traitée avec la refonte GUI.
  Le 2026-11-06, l'utilisateur a validé sous Windows l'analyse LIVE de 44 bougies M1 sur la
  Barrière Achat US Tech : trois stratégies affichées, dont `trend_follow` BUY, avec contexte,
  risque et coûts explicitement inconnus plutôt que complétés artificiellement.
- La connexion ne demande plus à IG de basculer vers le compte déjà déclaré courant par la réponse
  d'authentification. Cette requête redondante provoquait en DEMO un HTTP 412
  `accountId-must-be-different`; une sélection réellement différente conserve la bascule et son
  contrôle strict de confirmation.
- Les changements de compte et de connexion invalident les anciennes cotations, l'évaluation Paper,
  le graphique et le résultat Scanner ; les messages d'une ancienne génération de flux sont
  ignorés. Si la bascule échoue, l'application se déconnecte et ne mémorise pas le compte demandé
  comme confirmé. Tests hors ligne réussis ; la session DEMO déjà ouverte n'a pas été interrompue.
  La fenêtre refuse aussi un identifiant retourné différent de celui demandé ; l'adaptateur actuel
  reconstruit toutefois cet identifiant après succès HTTP, ce contrôle n'est donc pas une preuve
  indépendante fournie par IG.
- Les nouveaux journaux de souscription masquent l'identifiant complet du compte dans les noms
  d'items ; les anciens journaux ne sont pas modifiés. Après filtrage de la liste des produits,
  la dernière cotation de session reste affichée sans rafraîchir son horodatage Paper ; une
  infobulle distingue valeur de session et snapshot sans garantir leur fraîcheur.
- Une cotation IG explicitement signalée différée ne peut plus valider un ticket Paper, déclencher
  ou clôturer manuellement une position Paper, fournir son mark ou le spread du Scanner. Les
  tests synthétiques couvrent également le retour à une cotation non différée. Un marqueur absent
  ou non reconnu reste inconnu et ne constitue pas une preuve de fraîcheur.
- Le spread Scanner et le mark/la clôture manuelle Paper exigent désormais une cotation de session
  reçue depuis au plus 30 secondes ; une date future est refusée. La restauration d'une ancienne
  cotation ou une déconnexion/bascule invalide le prix utilisable sans fermer de position. La vue
  Paper se recalcule à son ouverture, à réception de cotations et, tant que l'onglet reste ouvert,
  lorsque le prix ou P&L change de fraîcheur. La position et la saisie de stop sont conservées ;
  l'action de clôture revérifie l'âge du prix. L'utilisateur a confirmé sous Windows qu'une position Paper sauvegardée est
  restaurée après redémarrage et reprend ses mises à jour. Le délai de péremption, le filtrage et
  les cas de bascule restent à valider séparément en réel ou par leurs tests hors ligne existants.
  L'utilisateur confirme aussi la reprise des mises à jour Paper après déconnexion/reconnexion ;
  l'état du mark durant la coupure n'a pas été explicitement rapporté.
- Une directive d'analyse hors broker joint désormais un signal, son score Scanner, son consensus
  et, si la politique l'exige, une analyse IA alignée, fraîche, bien cadrée et suffisamment
  confiante. Tout désaccord, risque bloqué, expiration ou veto donne `NO_TRADE`. Même `READY`, cette
  directive ne contient ni compte, ni quantité, ni ticket, ni `OrderIntent`. Un service séparé
  peut maintenant la convertir en brouillon Paper avec compte, cotation et quantité explicites,
  uniquement si identité, expiration et zone d'entrée concordent. Il produit le `TicketDraft` et
  le `RiskRequest` associé, sans évaluer le risque, réserver l'exposition, ouvrir une position ou
  appeler IG. Une frontière supplémentaire peut maintenant soumettre ce brouillon à
  `RiskEngine.evaluate` et conserver la décision ainsi que l'origine des limites. Même
  `APPROVED`, cette revue ne réserve ni n'autorise rien et exige encore une action opérateur
  explicite. Une frontière locale distincte implémente maintenant cette action : confirmation
  obligatoire, expiration revérifiée, nouvelle décision/réservation atomique sur le snapshot
  courant, puis seulement autorisation et soumission au `PaperBroker`. L'appel est idempotent et
  n'est déclenché automatiquement par aucun runtime ; aucun adaptateur IG n'est accessible.

## Prochaine étape recommandée
- Résoudre la paire Barrière Or canonique avec une preuve IG plus forte ou un choix opérateur ; ne
  pas déduire ce lien des noms dupliqués. La future liste classée et la refonte visuelle restent
  regroupées dans le chantier GUI dédié. Aucun choix AUTO ne doit être déduit des valeurs preview
  ou activé par défaut.

## Modules principaux
- Contrats d'adaptateurs et mappings, modèles/services de risque, analyse/scanner, PaperBroker/pending/trade manager et journal, SQLite explicite, analytics P&L, adaptateurs IG REST/streaming, services de données de marché et UI PyQt5.

## Commandes utiles
```bash
python scripts/codex/generate_repo_map.py --write --root .
python scripts/codex/verify_codex_pack.py
pytest -q
```

## Tests disponibles
- Tests pytest hors ligne après le passage temporaire aux bougies de session M1 sans historique
  REST/cache, l'agrégation locale des timeframes et le warmup explicite du Scanner ; dernière bougie
  exclue, aucun score partiel ni ordre. Runtime Trading Economics différé, OpenAI consultatif manuel
  ou périodique sur consentement de session,
  gate AUTO default-deny, replay, PaperBroker/pending/trade manager, contexte,
  stockage/récupération, journal/P&L, workspace, comptes/risque et données inclus.

## Dette connue
- Ruff repository-wide et format-check restent rouges sur des fichiers préexistants/générés hors périmètre R01 ; `ruff check src tests` passe.

## Risques ouverts
- Connexion LIVE read-only ajoutée à la GUI V2 mais restant à valider manuellement avec le profil
  utilisateur ; bougies et cotation directe Barrière ont été validées séparément.
  R07 a validé une seule séquence CFD DEMO bornée, non réutilisable comme autorisation générale.
  Barrières/Options/working orders, AUTO et exécution broker LIVE restent non supportés. Fuseaux IANA non-UTC
  indisponibles dans ce Python Windows sans `tzdata` ; aucun fallback temporel silencieux.
- Le runtime GUI ne consomme plus le quota historique IG. Après chaque redémarrage, les indicateurs
  techniques doivent se réchauffer depuis le flux M1 de la nouvelle session ; M5/H1 nécessitent
  mécaniquement beaucoup plus de temps que M1. Une coupure laisse un trou explicite et aucune donnée
  n'est reconstruite. Un fournisseur historique fiable reste une amélioration future, non bloquante
  pour le Paper manuel.

## Notes d'environnement
- Venv : `C:\Projects\TradingIG\.venv`
- OS : Windows
- Dépendances natives : aucune nouvelle dépendance ajoutée
- Matériel externe nécessaire : aucun pour la baseline hors ligne

## Reprise documentaire — 2026-10-22

- Dépôt inspecté : C:\Projects\TradingIG ; branche chore/sr41-upgrade ; HEAD 512c16d59337d2b92bb475daecb96cc902eb00c0 ; consolidation PRD locale préexistante préservée.
- [PRD V1.2 reconstitué](prd/PRD.md) depuis la V1.1 locale, avec autorisation utilisateur. Le pack V1.2 original de la conversation n'a pas été récupéré.
- [Mémoire de consolidation](codex/tasks/2026-10-22_prd-consolidation/task_plan.md) et [vérifications](codex/tasks/2026-10-22_prd-consolidation/verification.md).
- Code existant observé : package src/trading_ig_assistant, fenêtre PyQt, services de bougies et adaptateurs IG. Les méthodes d'ordre conservent LiveTradingDisabledError. R00–R03 ont fiabilisé données, contrats et risque ; R04 remplace les placeholders journal/persistance/analytics sans initialisation automatique de base ; R05 fournit le cœur d'analyse hors ligne sans chemin broker.
- Aucun statut DONE historique n'est déduit de l'existence des classes. Les anciens champs « à compléter » ci-dessus restent non évalués.
- SR 4.1 installé depuis la source officielle v4.1.0 (`596a681742e664dc9fdbbdc26783d62bba3f77f0`) après prévisualisation et validation humaine ; post-check vert et seconde prévisualisation idempotente.
- D-013 : héritage validé `global -> compte -> stratégie -> marché` ; l'origine de chaque valeur résolue reste inspectable.
- RepoMap régénérée après les ajouts structurels R02–R05 ; les cartes restent des aides, pas une preuve d'exécution.
- R05-AI1 fournit un contrat `MarketContextSnapshot` versionné et un fournisseur IA interchangeable : sortie exacte validée, sources actives citées, identité modèle/prompt, timestamps, validité et confiance. Une absence ou erreur reste `UNAVAILABLE/UNKNOWN`. Aucun fournisseur macro/news/LLM réel n'est configuré et aucune formule de stratégie métier n'est inventée ; le registre extensible, le consensus, les états et le scoring sont prêts pour ces implémentations explicites.
- R05-CTX1 ajoute `MacroEvent`, `NewsItem` et `MarketContextFlag`, les protocoles news/calendrier et une conversion contrôlée vers `ContextSignal`. Les sources futures, dupliquées ou absentes sont refusées ; des droits inconnus donnent un signal gris sans score ni confiance. Les fixtures sont synthétiques et aucun fournisseur réel n'est encore choisi.
- R05-SRC1 connecte en lecture seule les RSS officiels de politique monétaire de la Fed et de presse BCE. Les réponses et liens sont limités à des hôtes HTTPS autorisés, les tailles/délais sont bornés et les pannes deviennent `UNAVAILABLE`. Le smoke réel du 2026-11-04 a collecté 15 métadonnées par source. Le BLS est exclu car son endpoint a refusé l'automatisation ; aucun contournement n'a été tenté.
- R05-SRC2 lance ces collectes dans un worker `QThread`, au démarrage, toutes les 15 minutes et via
  une action Outils. Le ruban affiche uniquement leur santé agrégée ; le score et la confiance
  restent absents et les agrégats régime/indices/or/événements restent `unknown`.
- R05-AI2 ajoute un adaptateur OpenAI Responses optionnel : endpoint HTTPS officiel épinglé,
  secret injecté/redacté, modèle obligatoire sans valeur par défaut, stockage désactivé, taille et
  délai bornés, sortie JSON Schema stricte et refus/erreurs dégradés. Il n'est ni configuré ni
  appelé par le runtime ; un probe séparé exige modèle, plafond de sortie, clé d'environnement et
  accusé explicite. Le premier appel réel reste un gate humain coût/confidentialité.
- Le même probe est maintenant accessible dans Settings > OpenAI via un worker `QThread`. La GUI
  n'affiche que la présence de la clé, exige un modèle et un consentement explicites, et n'envoie
  qu'un contexte synthétique. Cette visibilité n'active ni le scanner, ni un outil web, ni IG.
- R05-AI3 projette au plus 20 titres officiels autorisés en `ai_evidence` grises, sans score ni
  confiance déterministe. Après un probe réussi dans la même session, une action Outils explicite
  lance l'analyse dans un second worker et affiche biais/risque/confiance/sources/expiration dans un
  chip IA séparé. R05-AI4 peut désormais relancer ce même worker toutes les 15 minutes, uniquement
  après un second consentement de session non persisté. Aucune recherche web, ticket ou chemin
  broker n'est ajouté.
- R06 simule coûts, spread, slippage, gap/KO et confirmations selon des hypothèses déclarées ; ces résultats ne prouvent pas le comportement IG. `PaperBroker` n'importe ni n'appelle l'adaptateur IG et les protections `LiveTradingDisabledError` restent couvertes.
- R08-2 agrège les positions Paper closes avec P&L net enregistré, risque initial, métriques R et drawdown ; l'enveloppe temporelle explicite bloque le look-ahead. Les fixtures synthétiques ne prouvent ni rentabilité, ni réalisme broker, ni aptitude AUTO.
- R08-3 convertit une série déjà chargée en dataset versionné puis expose les préfixes clos dans
  l'ordre ; une borne UTC explicite exclut la bougie courante/non close. Aucun signal ni trade n'est
  produit par ce flux générique.
- R08-4 évalue une stratégie injectée sur chaque préfixe et conserve la preuve source → signal ;
  identités, version, instrument, warmup et chronologie sont contrôlés. Aucune stratégie concrète,
  notation, intention ou exécution n'est ajoutée.
- R08-5 produit une empreinte SHA-256 canonique du dataset et des plans explicites
  train/validation/test ou walk-forward glissant ; aucun ratio implicite, accès aux partitions,
  optimisation ou résultat de performance n'est produit.
- La session GUI Paper reste en mémoire par défaut. Une action visible peut écrire un checkpoint complet dans SQLite v2 et une autre restaurer le dernier checkpoint ; aucune I/O base n'a lieu à l'import ou au démarrage, et une session active n'est jamais remplacée sans confirmation. Les positions ouvertes peuvent être resserrées ou clôturées explicitement dans cette seule session locale ; les vues Ordres et Journal restent des projections d'audit.
- Une devise produit absente d'IG peut être confirmée manuellement dans le ticket Paper ; elle n'est jamais déduite silencieusement. Une confirmation erronée reste un risque humain explicite.
- Les contrôles GUI actuels sont fonctionnels et provisoires ; la refonte visuelle globale est différée jusqu'à stabilisation des fonctions métier.
- TIG-INTEL-007 enrichit désormais au plus cinq actualités après consentement : extrait Tavily
  Search prioritaire, puis Extract Basic borné si nécessaire. L'interface affiche volume/coût
  estimés, extraits utilisés et liens sources. Les extraits restent en mémoire ; SQLite v3 ne
  conserve que les analyses, faits structurés, timestamps et références. GDELT dispose d'un
  circuit breaker Retry-After et ne bloque pas Tavily ni les sources officielles.
