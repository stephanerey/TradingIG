# Constats

- Le ticket transmet déjà des niveaux absolus au `TicketBuilder` et au moteur de risque.
- L'interface actuelle expose uniquement des niveaux absolus sans préremplissage.
- La conversion peut rester entièrement dans la vue : aucune règle broker ou modèle persistant
  n'a besoin d'être modifié.
- Le KO d'une Barrière représente un niveau produit distinct et ne doit pas être confondu avec
  une distance stop/objectif.
- Le choix provisoire par boutons radio tient dans le viewport 960×600 sans défilement horizontal.
- La refonte complète de l'interface est explicitement différée jusqu'à stabilisation des
  fonctions métier.

