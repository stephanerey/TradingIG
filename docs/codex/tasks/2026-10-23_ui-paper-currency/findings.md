# Findings

- La validation échoue avant le moteur de risque lorsque `product.currency` est vide.
- Le champ `Taux devise → EUR` ne peut pas remplacer la devise source absente.
- Les libellés actuels ne précisent pas que stop, objectif et KO sont des niveaux absolus.
- La Barrière reproduite devient évaluable après confirmation explicite `EUR`; les valeurs de la
  capture corrigée produisent une proposition approuvée dans le test et le smoke Qt.
- Le formulaire avait un débordement horizontal après l'ajout des libellés ; la politique de
  layout a été ajustée sans relever la taille minimale de la fenêtre.

