# Findings

- Le code OpenAI existant est uniquement accessible par le script CLI ; le runtime GUI ne le
  compose pas et l'onglet Application est un placeholder.
- `OPENAI_API_KEY` est détectée dans l'environnement du processus courant sans lecture ni affichage
  de sa valeur.
- La GUI existante utilise PyQt5 et impose les I/O réseau hors de la boucle Qt.
