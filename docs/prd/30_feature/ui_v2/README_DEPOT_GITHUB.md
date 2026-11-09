# TradingIG — Pack PRD GUI V2 / SR Method 4.1

**Édition : 2026-11-09 · Spécification GUI V2.0**

Ce pack est un **addendum modulaire**, pas une nouvelle base de code. Il reprend le style graphique sombre validé dans la conversation, décrit les huit pages, les règles de disponibilité des données, l'i18n FR/EN et un plan de refactorisation de la GUI PyQt5 pour Codex.

## Sommaire du pack

- `PRD_TradingIG_GUI_V2_Complet.pdf` : version de lecture, avec les maquettes originales en références visuelles.
- `PRD_TradingIG_GUI_V2_Complet.md` : consolidation Markdown pour lecture globale.
- `docs/prd/30_feature/ui_v2/*.md` : source de vérité modulaire pour GUI V2.
- `docs/prd/10_architecture/gui_v2_refactor.md` : **instructions de modification d'architecture**.
- `docs/prd/02_tasks/phases/R09_gui_v2.md` : ordre de migration Codex par lots SR 4.1.
- `docs/prd/05_coding_agent/gui_v2_codex_guide.md` : protocole de développement sûr.
- `docs/prd/90_quality/gui_v2_qa.md` : matrice d'acceptation.
- `docs/prd/95_sources/images/ui_v2/` : illustrations approuvées de direction graphique.
- `PROMPT_CODEX_DEMARRAGE_GUI_V2.md` : message à donner à Codex après installation.
- `requirements_traceability.csv` : inventaire automatisé des exigences GUI2.
- `install_gui_v2_docs.py` : simulation/idempotence ; ne remplace JAMAIS un fichier existant différent.

## Pourquoi ne pas écraser le PRD actuel ?

Le dépôt dispose déjà de `docs/prd/PRD.md`, F001–F013, des tâches R00–R08 et d'une infrastructure SR 4.1. Le présent pack ajoute un sous-dossier **`ui_v2`** et des documents à nouveaux noms sans toucher aux anciens fichiers. Codex devra ensuite proposer une petite mise à jour du `docs/prd/PRD.md` et de F012, avec revue des éventuels conflits. **Ne pas supprimer** la structure préexistante.

## Installation via GitHub

Cette branche `docs/gui-v2-prd` contient déjà les documents. Aucun ZIP ni script d'installation n'est nécessaire.

```powershell
cd C:\Projects\TradingIG
git fetch origin
git switch docs/gui-v2-prd
# si la branche locale n'existe pas : git switch --track origin/docs/gui-v2-prd
```

Ne pas fusionner dans `main` ou `chore/sr41-upgrade` sans revue. Lire le guide Codex et lancer la phase R09-00 de cartographie, sans mutation applicative.

## Sources et statut

Révision Git observée lors de la rédaction : `stephanerey/TradingIG`, `chore/sr41-upgrade`, `1844916acec43d5ef0dc692d5235214dc46c5a9b` du 9 novembre 2026. Les **606 tests** mentionnés dans l'état remis par Codex ont été exécutés localement par Codex et n'ont pas été rerun ici. Les états de trading et les chiffres affichés dans les maquettes sont fictifs. Aucun chemin LIVE/AUTO d'ordre n'est autorisé par ce pack.