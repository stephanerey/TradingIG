# DESIGN.md — TradingIG

## Objectif
Décrire les conventions d'interface et d'expérience du projet Python.

## Type de projet
À préciser : CLI, application desktop Qt, librairie Python, pipeline de données, script matériel, service local, notebook, outil interne.

## Règles générales
- Interface claire, prévisible, sans magie cachée.
- Logs exploitables : niveau, module, timestamp, message court.
- Erreurs explicites : ne pas avaler les exceptions sans contexte.
- Paramètres configurables par fichier, CLI ou profil, pas par constantes dispersées.
- Les exemples doivent être reproductibles localement.

## Applications Qt / PyQt / PySide
- Ne jamais bloquer le thread GUI.
- Utiliser signaux/slots pour communiquer entre workers et UI.
- Éviter les accès directs aux widgets depuis un worker.
- Centraliser les noms de widgets QtDesigner et vérifier avec `findChild`.
- Garder les styles QSS séparés du code logique.
- Mettre les traitements longs dans `QThread`, `QRunnable`, `asyncio/qasync` ou un worker dédié selon l'architecture existante.

## CLI / scripts
- Prévoir `--help` clair.
- Codes de retour explicites.
- Sortie compacte par défaut, mode verbose si besoin.
- Ne pas écrire dans le répertoire courant sans option documentée.

## Data / plots
- Ne pas charger de très gros CSV sans stratégie mémoire.
- Séparer chargement, transformation, validation et affichage.
- Documenter les colonnes attendues.
- Ne pas modifier les fichiers source sans backup ou sortie explicite.
