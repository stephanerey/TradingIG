# Plan SR — Fusion explicable du contexte

1. Conserver le dernier `MarketContextSnapshot` dans le runtime GUI, sous
   controle de generation et sans abonnement UI supplementaire.
2. Publier ou invalider ce contexte depuis le controleur Macro/IA au meme
   moment que la projection lisible.
3. Injecter le `MacroRibbonState` et le snapshot IA dans le scanner existant,
   qui applique deja portee, fraicheur, provenance et veto de risque.
4. Tester la publication, l'invalidation, le rejet des generations obsoletes
   et le raccordement exact des arguments du scanner.
5. Executer lint cible, tests cibles, suite complete et controles SR.

Ce lot ne cree ni ordre, ni ticket, ni action broker. En l'absence de preuve
attestee, la valeur reste explicitement `UNKNOWN`.
