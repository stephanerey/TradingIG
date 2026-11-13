# Constatations

- Le depot possede deja `NewsItem`, `NewsProvider`, Fed/BCE RSS et une frontiere
  Qt worker ; ils sont reutilisables.
- `NewsItem` impose une date UTC. Une date Tavily absente sera donc representee
  par l'heure d'observation et un statut explicite `unknown`, jamais comme heure
  certaine de l'evenement.
- L'API Tavily documente actuellement `topic=general|news`, pas `finance`.
- Le projet ne depend d'aucun client HTTP tiers ; les adaptateurs utilisent la
  bibliotheque standard avec transports injectables.
- La branche contient de nombreuses modifications GUI V2 non commitees ; elles
  sont preservees.
- Tavily peut renvoyer des elements plus anciens que `max_age_hours` et son
  classement peut varier entre deux recherches identiques. Le filtre de
  fraicheur fournisseur ne suffit donc pas comme preuve : la borne est aussi
  controlee localement et les resultats recents sont stabilises cote runtime.
- L'IA ne recoit actuellement que des metadonnees. Un enrichissement par contenu
  constituerait un contrat distinct, borne et transient ; il ne doit pas
  transformer la collecte de decouverte en archivage integral des articles.
