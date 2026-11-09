# Findings

- `SetupScoringService` refusait déjà un total si une composante était absente et faisait primer
  les vetos ; ce comportement est conservé.
- Les signaux exposent les niveaux et la qualité nécessaires aux composants technique, R/R et
  qualité.
- Le runtime ne dispose pas encore d'un coût complet et fiable par produit : le spread peut être
  observé, mais les frais ne doivent pas être supposés nuls.
