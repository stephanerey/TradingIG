# Décisions

- Les frais restent globaux : aucun nouvel héritage compte/stratégie/marché n'est introduit.
- Les décimales sont persistées sous forme de chaînes exactes.
- Coût aller-retour par unité = spread de session + deux côtés de frais.
- Le calcul exige le même epic pour le produit coté et la source des niveaux techniques.
- Les snapshots de découverte ne remplacent pas une cotation de session pour ce calcul.
- Le profil indicatif est daté, visible et restaurable ; son initialisation est persistée afin
  qu'un champ volontairement effacé ne soit pas rempli à nouveau au redémarrage.
- Les CFD actions sont exclus du forfait par unité : leurs commissions nécessitent un futur modèle
  en pourcentage avec minimum.
