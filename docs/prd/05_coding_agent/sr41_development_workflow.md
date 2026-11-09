# SR 4.1 Development Workflow — Target, Not Installed State

> **PRD Policy:** **PROJECT (editable)** — TradingIG V1.2 reconstructed from the recovered V1.1.

**Last updated:** 2026-10-22

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 18; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-18"></a>

## 18. Plan d’implémentation obligatoire pour Codex

Le développement est incrémental, avec test de sortie à chaque tranche et **pas d'accès live** avant jalon formel. Chaque phase dispose de tâches courtes, mesurables et revues.

| Phase | Contenu | Critère de sortie (Definition of Done) |
|---|---|---|
| **SR00 — Migration SR 4.1.0** | Diagnostic en lecture seule, preview officielle de la mise à niveau de l’ancien pack, validation humaine, upgrade SR seul puis contrôles | `SR_PACK_VERSION.json=4.1.0`, `sr_post_install_check` concluant, aucun fichier applicatif modifié ; **arrêt avant R00** |
| **R00 — Baseline** | Branche de travail depuis `512c16d`; inventaire diffs, dépendances, tests, capture GUI, état des comptes | `pytest`/Ruff/smoke documentés ; aucune écriture live ; fiche `CURRENT_STATE.md` à jour |
| **R01 — OHLC** | Corriger BUG-DATA-001/002/003 ; compaction après ; tests M1→M5, quota, non-blocage UI | Fixtures OHLC exactes, cache accessible quota épuisé, thread Qt non bloqué |
| **R02 — Contrats** | Introduire interfaces Broker/Data et capacités ; mapping sous-jacent/contrat, fake adapters | Tests contractuels multi-providers ; GUI existante conserve son comportement |
| **R03 — Comptes et risque** | Account Manager, snapshots, calculs equity, plafonds 1 %/3 %, limites global/marché | Tests multi-comptes, FX, réservations concurrentes, veto et kill switch |
| **R04 — Stockage & GUI** | Event Store, recorder, migrations, statistiques et nouveaux tabs/docks, settings complets | P&L recomptable, stats jour/semaine/mois, settings tous éditables, migration testée |
| **R05 — Analyse** | Indicateurs, stratégie registry, macro/sentiment, scanner, scoring, commentaire | Fixtures numériques, `WARMING_UP`, `NO_TRADE`, justifications auditées |
| **R06 — Paper & trade manager** | Ticket builder, PaperBroker, ordres conditionnels, sécurisation + trailing, alerts | Parcours paper intégral, confirmations fictives, aucun appel live, tests state machine |
| **R07 — API IG démo/supervisé** | Capability matrix Barrières/Options et CFD, order coordinator, réconciliation et confirmations | Tests démo et dossier preuves sanitizées ; supervised gate ; cas timeout/compte incorrect |
| **R08 — Automatisation optionnelle** | Activation AUTO, whitelists, surveillance, validation quantitative, exploitation | Kill switch/risk veto testés, reprise sûre, critères d'acceptation signés ; aucune activation implicite |

**Règle :** Codex ne saute pas une phase sans justifier explicitement la conformité des prérequis et les preuves de test. L'amélioration fonctionnelle peut être découpée davantage, mais les garde-fous ne sont jamais reportés après les appels live.

### 18.1 Tranche R00/R01 — seulement après SR00 vérifié

1. Vérifier `git status`, l'ancêtre de `main`, créer `codex/tradingig-prd-v1-restart` depuis `codex/stream-live-candle-robustness` (ne pas modifier `main` directement).
2. Installer dans un venv du dépôt les dépendances du `pyproject.toml`, identifier toute divergence Python 3.11/3.12 et verrouiller l'environnement choisi.
3. Exécuter `pytest -q`, `ruff check src tests` et smoke GUI ; noter résultats sans modifier la logique pour faire artificiellement passer les tests.
4. Ajouter test du **cache lisible malgré quota historique global épuisé**, puis corriger l'ordre de priorité dans `MainWindow`.
5. Ajouter test M1→M5 avec 5 bougies, ordres de mises à jour et valeurs extrêmes variées ; corriger le calcul canonique ; vérifier partiel/clôturé.
6. Séparer l'appel REST historique bloquant de la boucle Qt ; ajouter test avec faux provider lent et interaction GUI non bloquée.
7. Vérifier après patch : relecture cache, recalcul timeframes, changement de produit, Bid/Mid/Ask, reconnexion et sélection de compte.
8. Documenter `findings.md`, `progress.md`, `verification.md`, décisions/ADR, modifications et risques restants ; ne pas créer de fonction de trading réel.

### 18.2 Pratique Codex sous SR 4.1.0

- Après mise à niveau SR00, lire le **noyau court** de `AGENTS.md` et la route pertinente dans `docs/codex/SR_ROUTES.json` ; ne charger que les procédures déclenchées et les sources de code réellement nécessaires. Pour une modification non triviale, les contrôles SR sont **Scope**, **Verification** et, uniquement si une activation est demandée, **Activation**.
- Les skills spécialisés sont conditionnels : `aurora-diagnose` pour un bug réel, `aurora-architecture-check` pour une interface/schéma, `aurora-ui-visual-qa` pour une modification graphique, `aurora-lot-runner` pour une passe multilot validée. `aurora-to-prd` et `aurora-domain-skill-factory` restent facultatifs. Ne pas importer l’ancien catalogue de 10 skills comme règle 4.1.
- Conserver `docs/prd/PRD.md`, les fiches `F001..F011` et `docs/CURRENT_STATE.md` comme documents produit/projet à tenir alignés. Ce PDF/MD est la **baseline produit du 20 octobre 2026** ; les registres SR et la documentation modulaire sont la mémoire d’exécution.
- Présenter le périmètre et la preuve de validation proportionnelle à chaque tranche. Les tests de non-régression critiques restent obligatoires pour notre trading, **sans imposer le rituel TDD ni un test délibérément rouge**, retirés de SR 4.1.
- Ne jamais effectuer un appel IG d’ordre réel, un changement de compte actif ou une migration/déploiement sans autorisation spécifique ; aucune donnée secrète dans les artefacts.

### 18.3 SR Method 4.1.0 — contrat de développement obligatoire

**SR (Specification Runtime Method) est une méthode de pilotage de Codex et non une stratégie de trading.** Le dépôt contient déjà un pack Codex hérité (état constaté sur `codex/stream-live-candle-robustness`, mai 2026) avec `AGENTS.md`, scripts, RepoMap et mémoires de tâches. **Il ne doit pas être considéré comme SR 4.1.0 installé avant vérification.**

**Référence officielle :** [Aurora SR Method Codex Pack](https://github.com/syl2042/Aurora_SR_method_codex_pack) ; version publiée `4.1.0` le **24/09/2026**, d’après `core/SR_PACK_VERSION.json`, `CHANGELOG.md` et `INSTALLATION.fr.md`. Ne pas utiliser les consignes plus anciennes du site ou les historiques mémorisés pour substituer un autre catalogue de skills à la version 4.1.

#### 18.3.1 SR00 — migration indépendante du code applicatif

1. **Lecture seule :** sélectionner la branche de travail fondée sur `codex/stream-live-candle-robustness`, contrôler `git status`, versions/empreintes SR présentes et travail local non committé. Ne pas fusionner `main` ni modifier le code.
2. **Source explicite :** pointer `SR_PACK_SOURCE` vers le dépôt officiel ; vérifier URL, commit source, état Git, `version=4.1.0` et `release_status=released`. Enregistrer ce commit dans le rapport SR00.
3. **Prévisualisation uniquement :** exécuter le plan officiel sans écriture : `python scripts/install_codex_pack.py --source <SR_PACK_SOURCE> --target <TradingIG> --json` (avec l’interpréteur du venv et les chemins Windows adaptés). Classer les fichiers absents, gérés, personnalisés, obsolètes ou conflictuels.
4. **Validation humaine :** soumettre la liste exacte des fichiers qui seront modifiés, préservés et éventuellement supprimés. **Ne pas passer à `--upgrade` sans approbation de cette liste**, même si le présent PRD est validé.
5. **Upgrade conservateur :** seulement après validation, utiliser `--upgrade` pour une installation ancienne, partielle ou modifiée. Ne pas réinstaller en mode neuf `--write` quand des marqueurs SR existent. Préserver toutes les mémoires, lots, passes, handoffs, compétences locales, instructions personnalisées, travaux non committés et artefacts métier.
6. **Contrôle :** exécuter `scripts/codex/sr_post_install_check.py --root . --json`, `git diff --check`, `git status --short` et les vérificateurs SR réellement présents. Un code de sortie installateur `0` seul **ne prouve pas** la conformité. Si le rapport est rouge, classer SR00 comme incomplet.
7. **Fin de SR00 :** livrer versions, source commit, conflits, état des skills, vérifications, chemins modifiés et dérogations ; **arrêter avant de coder R00/R01**. Si nécessaire, proposer le réalignement mémoire en suivant `prompts/fr/07_realign_sr_state_after_upgrade.md`, avec validation séparée. Ne fermer aucun lot applicatif par effet de bord.

**Interdictions durant SR00 :** toucher `src/`, les tests métier, `pyproject.toml`, les secrets, les migrations SQLite, les positions/ordres, les paramètres de trading, ou activer des outils MCP/Nexus. La migration SR n'est ni une mise à jour applicative ni un déploiement.

#### 18.3.2 Fichiers SR et hiérarchie d'autorité

| Artefact | Usage attendu après upgrade |
|---|---|
| `AGENTS.md` | Noyau court de règles permanentes, routes et garde-fous TradingIG ; préserver les règles locales |
| `docs/codex/SR_BOOTSTRAP.md`, `SR_ROUTES.json` | Procédures à lire selon l'action, pas chargement systématique du pack |
| `docs/codex/PROJECT_PROFILE.yaml`, `SKILL_DIGEST.md` | Configuration `knowledge.mode`, sélection exacte de skills ; pas d'ancien catalogue obligatoire |
| `docs/codex/SR_LOTS.yaml`, `SR_PASSES.yaml`, `SR_INBOX.yaml` | Backlog atomique, passes bornées, demandes/décisions à trier ; zéro lot inventé à l'installation |
| `docs/codex/tasks/.../task_state.yaml` | Mémoire compacte d'une tâche non triviale ; anciens `task_plan`, `findings`, `verification` restent lisibles |
| `docs/CURRENT_STATE.md`, `CODEBASE_MAP.md` | Reprise fondée sur l'état réel ; code et tests prévalent sur la carte et les résumés |
| `docs/codex/MCP_POLICY.yaml` | Politique de capacités MCP ; mode `core` par défaut et **aucun MCP** en ce mode SR |
| `docs/codex/project-skills/` | Skills de domaine TradingIG locaux après validation humaine, pas de publication globale automatique |

**Autorité :** spécifications approuvées (`REQ-*` et décisions), code réel et tests pour les faits d'implémentation, registres SR pour l'état du travail. Ne jamais convertir massivement les anciens contrats SR, ni effacer leurs preuves pour les aligner visuellement.

#### 18.3.3 Exécution des lots et trois frontières

- **Scope Gate (avant mutation non triviale) :** expliciter résultat observable, chemins autorisés, fichiers sensibles, hypothèses, contrats/consommateurs affectés, risque, tests ciblés et limites de la tranche. Demander autorisation si changement de périmètre, schéma critique ou couplage externe.
- **Verification Gate (fin du travail) :** valider à coût proportionné aux risques : tests unitaires/contrats/replay ciblés, `ruff`, imports, contrôle de logs/secrets, vérification des conséquences sur les consommateurs. Les tests d'ordres, de positions, de risque, d'OHLC et de réconciliation sont **indispensables selon leur périmètre** ; SR 4.1 n'impose ni TDD cérémoniel ni faux échec initial.
- **Activation Gate (seulement pour build, redémarrage, déploiement ou activation demandés) :** expliciter l'artefact activé, preuves du runtime et procédure de retour arrière. Dans TradingIG, activer la voie réelle `SUPERVISED`/`AUTO` est une autorisation sensible **distincte de l'autorisation de développer du code**. Aucun accès live créé/activé pendant SR00–R06.

Pour les changements étendus, grouper des lots cohérents dans une *SR Pass* approuvée, vérifier dépendances, ne pas multiplier les micro-validations, arrêter sur vraie décision bloquante. Une tâche simple peut se terminer sans nouvel artefact SR. Les bilans doivent distinguer **fait**, **vérifié**, **non vérifié** et **acceptation humaine restante**.

#### 18.3.4 Domain skills et méthode des agents IA runtime

Proposer, mais **ne pas créer sans validation**, des compétences locales TradingIG : `tradingig-ig-api-capabilities`, `tradingig-market-data-integrity`, `tradingig-risk-and-order-safety`, `tradingig-pyqt-windows-qa`. Elles décrivent les pièges du domaine et les sources de vérité, non de nouveaux privilèges d'exécution.

Les futurs agents IA de sentiment ou de trading doivent respecter le **SR Agent Method** : action produit bornée, entrée et sortie typées, provenance/fraîcheur, distinction outil de lecture / action d'ordre, contrat d'agent et validation humaine pour toute action sensible non déléguée. L'autorisation AUTO, lorsqu'elle sera explicitement accordée, reste soumise au moteur de risque déterministe, aux limites de positions et à la réconciliation du broker.

La configuration initiale de connaissance sera `knowledge.mode: core`, **sans appels MCP** dans ce mode de fonctionnement Codex. Toute activation future `nexus_kg` requiert une décision séparée et une `MCP_POLICY.yaml` explicite (outils autorisés, lecture/écriture, confidentialité, budgets, retries et approbations). Cela ne proscrit pas les appels réseau métier IG de l'application : la règle MCP concerne les outils de connaissance de Codex.

#### 18.3.5 Vérification UI adaptée à Windows/PyQt5

Les vérifications visuelles de SR 4.1 sont déclenchées pour une modification graphique significative. **TradingIG étant une GUI native PyQt5, il ne faut pas supposer qu'une URL Playwright existe.** Codex proposera la voie réellement disponible : tests Qt ciblés, captures d'écran Windows hors données sensibles, scénarios utilisateur M1/M5 et comptes, et rapport d'inspection visuelle. Le runner web SR ne sera utilisé que pour un éventuel composant web réellement présent.

**Critères d'acceptation méthode SR :** `AC-SR-001` source publiée et commit enregistré ; `AC-SR-002` migration sans mutation métier ni perte des personnalisations ; `AC-SR-003` post-install check satisfaisant ; `AC-SR-004` reprise à partir du véritable état de la branche avancée ; `AC-SR-005` aucun ordre réel ou déploiement implicite ; `AC-SR-006` traçabilité exigences → lots → preuves → validation.
