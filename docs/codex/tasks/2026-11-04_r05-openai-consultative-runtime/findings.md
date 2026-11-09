# Findings

- Le refresh Fed/BCE conserve déjà les `NewsCollectionSnapshot`, mais la fenêtre ne gardait que le
  signal de santé des sources.
- Le contrat IA existant exige une citation de `ContextSignal` active ; les métadonnées news doivent
  donc être projetées sans inventer de sévérité ni de score.
- Le ruban projette actuellement tous les signaux ; les preuves IA grises doivent rester dans la
  provenance sans encombrer l'affichage.
- Le premier essai humain a bien déclenché le runtime mais s'est dégradé en `AI: unavailable` ; la
  journalisation initiale ne distinguait pas `AI_PROVIDER_ERROR` de `AI_OUTPUT_INVALID`.
- Le schéma initial demandait des chaînes libres pour `source_signal_ids`. Le guide officiel
  Structured Outputs autorise `enum`, `minItems` et `maxItems` : les citations peuvent donc être
  contraintes aux identifiants exacts fournis au modèle.
- Un signal `data_health` prouve seulement la disponibilité d'une source et ne doit pas être une
  citation admissible, même lorsque son état est vert.
- La seconde validation humaine affiche `AI: unknown / risk unknown` et la trace sûre confirme
  `status=available`, modèle `openai-responses:gpt-6-luna`, sans raison d'échec.
- Le test a aussi révélé un verrou Windows pendant la rotation quotidienne du journal lorsqu'un
  autre processus conserve le fichier ouvert ; la rotation est maintenant différée sans perdre la
  ligne courante ni répéter une traceback pour chaque événement.
- Une reconstruction du contexte, par exemple après mise à jour du calendrier, renouvelait
  artificiellement la validité d'une collecte Fed/BCE ancienne. De plus, le contrôle GUI de preuve
  vérifiait son tag mais pas son expiration. La validité dépend désormais de la collecte réelle,
  les signaux expirés/futurs ne sont plus transmis au fournisseur et le contexte de l'appel GUI
  est recalculé à l'heure courante. L'âge de publication d'un titre n'est pas assimilé à une durée
  de pertinence métier : aucune durée de ce type n'a été inventée.
- Un snapshot macro pouvait conserver un agrégat directionnel ou de risque après expiration de ses
  signaux ; la projection produit et le Scanner réévaluent désormais leur état au moment de l'usage.
- Une analyse IA future ou expirant exactement à l'instant courant pouvait encore influer sur un
  produit ; un catalyseur était lui aussi accepté à sa limite d'expiration. Les bornes sont désormais
  cohérentes avec la directive d'analyse (`génération <= maintenant < expiration`).
- Le ruban IA ne réagissait ni à l'expiration de l'analyse, ni au changement de marché. Un minuteur
  Qt local met l'affichage à jour, sans nouveau fournisseur ni appel OpenAI.
