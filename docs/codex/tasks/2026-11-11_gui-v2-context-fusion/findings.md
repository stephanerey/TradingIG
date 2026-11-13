# Constatations

- Le moteur de projection produit savait deja appliquer portee globale,
  produit exact, binding de reference, expiration, provenance et risque.
- Le controleur Scanner ne transmettait ni `MarketContextSnapshot` ni son
  `MacroRibbonState` et remplacait ces donnees par un objet inconnu local.
- Le resultat IA global n'est pas transforme en signal produit : il contribue
  uniquement au composant de contexte, avec la portee et la fraicheur attestees.
- Les analyses actuelles `UNKNOWN / WAIT` resteront inconnues dans le scanner,
  ce qui est le comportement de securite attendu.
