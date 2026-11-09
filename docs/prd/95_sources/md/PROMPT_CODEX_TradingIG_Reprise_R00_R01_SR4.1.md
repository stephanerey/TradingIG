# Prompt Codex — TradingIG R00 / R01 après SR00 validé

Tu interviens dans le dépôt **`stephanerey/TradingIG`** **après validation et vérification de la migration SR00 vers SR Method 4.1.0**, conformément au **`PRD_TradingIG_V1.1_SR4.1_2026-10-20.md`** et au rapport **`TradingIG_Audit_Reprise_2026-10-20.md`**. Le PRD est une spécification produit ; il complète la documentation modulaire du dépôt, qui doit rester l'unique source opérationnelle de suivi des tâches.

**Précondition bloquante :** vérifier dans le dépôt le rapport SR00, `docs/codex/SR_PACK_VERSION.json` (release 4.1.0) et le post-check satisfaisant. Sinon **STOP**, revenir au prompt SR00. Respecter `AGENTS.md` allégé, `SR_ROUTES.json`, trois gates SR 4.1 Scope/Verification/Activation, `knowledge.mode: core`, et les compétences conditionnelles ; utiliser un état de tâche compact si utile, et préserver les contrats legacy.

## Règles non négociables

1. **Ne reconstruis pas l'application depuis zéro.** La branche de travail doit dériver de `codex/stream-live-candle-robustness`, commit de référence `512c16d59337d2b92bb475daecb96cc902eb00c0`. À la date de l'audit, cette branche avait 60 commits d'avance sur `main` et 0 en retard ; **revérifie avant toute modification**.
2. Travaille sur une **nouvelle branche dédiée** après avoir vérifié `git status` et les références distantes. Ne pousse ni ne fusionne sur `main` sans revue.
3. Lis d'abord `AGENTS.md`, `docs/prd/PRD.md`, `docs/prd/PRD_READY_CHECKLIST.md`, `docs/codex/CODEBASE_MAP.md` et le nouveau PRD. Examine le code réel avant de proposer un refactoring.
4. **Aucune création/modification/fermeture d'ordre IG en réel** dans R00/R01. Ne supprime pas `LiveTradingDisabledError` ni les protections read-only.
5. Ne demande, ne stocke et n'affiche **aucun secret** (API key, mot de passe, CST/XST, tokens, IDs de compte exportables). Pas de fichier `.env` suivi par Git.
6. Aucune réécriture massive ni dépendance ajoutée sans justification et tests. Préserve PyQt5/PyQtGraph, les widgets déjà fonctionnels et les comportements du streaming.

## Phase R00 — Baseline (commencer en lecture seule)

- Confirme branche/commit, état Git, différences de `main`, version Python effective et dépendances installées.
- Décris brièvement les classes/services actuels, leurs responsabilités et ce qui est effectivement implémenté (adapter IG REST, Lightstreamer, produits, charts, cache, workers).
- Exécute `pytest -q` et `ruff check src tests` dans un venv local ; si possible, lance un smoke test GUI Windows hors connexion IG. **Rapporte tous les échecs observés sans les masquer.**
- Documente les lacunes dans le `task_state.yaml` compact (ou les mémoires legacy déjà présentes) et le rapport de vérification adapté et actualise `docs/CURRENT_STATE.md` si nécessaire.
- Ne passe à R01 qu'avec une baseline identifiée et reproductible.

## Phase R01 — Correctifs prioritaires et vérifications proportionnées SR 4.1

1. **Cache local vs quota API** : ajouter le test `cache présent + _api_allowance_exceeded=True + client REST mock qui échoue si appelé`. Le graphique doit charger le cache, REST ne doit pas être appelé. Corriger le chemin `MainWindow._load_selected_product_history()`.
2. **Agrégation OHLC** : ajouter une fixture à cinq bougies M1 avec high/low extrêmes et au moins une mise à jour d'une sous-bougie. Le fallback M1→M5 doit calculer open de la première minute, high maximum, low minimum, close de la dernière minute, volume cohérent, fermeture et horodatages corrects. Corriger sans briser les timeframes directs IG.
3. **I/O hors GUI** : démontrer par test (faux provider lent) que la récupération REST historique et le fallback ne bloquent pas la boucle Qt. Déplacer les appels réseau des handlers GUI vers des workers/services, avec signaux/slots sûrs.
4. Tester les régressions sur résolution M1/M5, Bid/Mid/Ask, cache relu après redémarrage, sélection de produit, déconnexion/reconnexion et sélection de compte.

SR 4.1 n’impose **pas** de workflow TDD ni de tests artificiellement rouges ; les tests réels de régression listés ci-dessus restent des critères d’acceptation métier obligatoires. La vérification graphique doit cibler la GUI PyQt5 Windows (pas de supposition de site Playwright).

Les problèmes P1 (compaction cache JSONL, sélection de compte échouée, nettoyage du module `MainWindow`) seront planifiés et pourront être traités après ces correctifs, sauf si un patch minimal est indispensable à R01.

## Livrable attendu de Codex après R00/R01

- Résumé du diagnostic et de la baseline.
- Liste des fichiers modifiés avec justification.
- Tests ajoutés, commandes exécutées, résultats et éventuelles limitations environnementales.
- Diff revu, risques de régression et points non résolus.
- Mise à jour du suivi des tâches et proposition de la phase suivante R02.

**Ne commence pas R02 (multibroker) ni l'exécution d'ordres avant retour de validation.**
