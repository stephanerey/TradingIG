# Décisions

- Réutiliser exclusivement les primitives du `PaperBroker` existant.
- Les boutons agissent uniquement sur une position Paper ouverte explicitement sélectionnée.
- Aucun appel réseau, stockage, changement de stop IG ou clôture IG n'est ajouté.
- Un stop élargi est refusé par la frontière Paper et le refus reste visible et journalisé.

