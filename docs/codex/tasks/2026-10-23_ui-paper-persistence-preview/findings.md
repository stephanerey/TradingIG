# Constats

- Le schéma SQLite v1 déployé ne contient que `schema_migrations` et le journal append-only.
- Aucune base runtime n'existe actuellement à
  `C:\Users\srey\.trading_ig_assistant\data\trading_ig_assistant.sqlite`.
- La session Paper actuelle conserve en mémoire positions, soumissions, cotations, hypothèses et
  journal ; le seul journal v1 ne suffit pas à restaurer sûrement une position ouverte.
- Une table de checkpoints versionnés est le plus petit ajout permettant une reprise complète sans
  introduire un second format de stockage.
- Le pack R04 n'autorise que le schéma v1 ; l'extension v2 exige donc une nouvelle validation.

