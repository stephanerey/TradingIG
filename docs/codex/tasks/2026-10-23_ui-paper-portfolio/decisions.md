# Décisions

- La session Paper est locale et volatile ; aucune base SQLite n'est ouverte ou créée.
- Le ticket reste sans dépendance directe à `PaperBroker` ou à un adaptateur IG : il émet une
  demande typée vers la composition applicative.
- Le bouton d'ouverture porte explicitement le libellé Paper et déclenche une réévaluation
  complète avant émission.
- Les vues de ce lot sont read-only ; les contrôles de clôture/stop feront l'objet d'un lot séparé.

