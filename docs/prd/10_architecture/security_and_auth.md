# Security and Auth

> **V1.2 reconstruction — 2026-10-22:** [Project conventions](../00_conventions/tradingig_v1_2_conventions.md) and [reconciliation decisions](../01_product/decisions.md) apply. Earlier project text is preserved; explicit V1.2 changes take precedence only on documented conflicts. This is not implementation or activation evidence.


> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-11-04

## Goal
Protect IG account credentials and prevent accidental live trading.

## Credential configuration screen
The settings UI MUST allow the user to enter:
- IG username / identifier;
- IG password;
- IG API key;
- environment: DEMO or LIVE;
- account selection / preferred account ID after login;
- optional one-time/security code flow if required by IG;
- live-mode execution enablement flag.

## Storage policy
- Password and API key MUST be stored only in OS keyring or equivalent encrypted credential store if persistence is enabled.
- Non-secret settings MAY be stored in YAML/JSON.
- Session tokens MUST be memory-only unless a safer explicit design is approved.
- External AI API keys MUST follow the same OS keyring/encrypted-store rule and remain separate
  from IG credentials; until that storage path is implemented, keys may only be injected in memory.
- Exported journals and logs MUST NOT include secrets.

## Runtime safeguards
- Default environment MUST be demo or dry-run.
- Live execution MUST require explicit enablement and visible UI state.
- A global kill switch MUST disable order placement/update immediately.
- Account/environment indicator MUST be visible in trading views.
- Risk limits MUST be enforced regardless of UI state.

## Constraints
- Do not hardcode credentials in code, tests, fixtures, or docs.
- Do not use screenshots containing credentials as test fixtures.
- Any exception wrapping external responses must redact headers/tokens.

## Acceptance criteria
- Redaction tests pass.
- Credentials do not appear in config files after saving settings.
- Live mode cannot be enabled through config file editing alone without UI confirmation or explicit CLI flag.

## Testing notes
- Mock keyring in unit tests.
- Add tests with fake secret values and assert logs/config are clean.

## V1.2 consolidation

Provenance: [archived V1.1 of 2026-10-20](../95_sources/md/PRD_TradingIG_V1.1_SR4.1_2026-10-20.md), chapter 16; [chapter mapping](../00_conventions/v1_2_source_coverage.md). Claims about implementation, external APIs and the SR release remain dated source assertions unless separately verified. References such as §8 refer to the original numbered chapters in that mapping.

<a id="source-section-16"></a>

## 16. Sécurité, déploiement et exploitation

**REQ-SEC-001/P0** Secrets non stockés en clair dans config YAML/JSON ni dans git ; utiliser Windows Credential Manager via `keyring` ou fournisseur sécurisé équivalent.\
**REQ-SEC-002/P0** Séparer environnement `DEMO` / `LIVE`, profils de clés et identité du compte ; confirmation explicite avant première activation LIVE de chaque compte.\
**REQ-SEC-003/P0** `AUTO` nécessite activation explicite locale, stratégies et marchés autorisés, bornes de risque, kill switch, validation API et absence de défauts critiques ; persistance du paramètre d'autorisation à préciser avec prudence (démarrage sûr).\
**REQ-SEC-004/P1** Packaging Windows reproductible, installation documentée pour Python 3.12 / venv puis livrable exécutable packagé dans une phase ultérieure (ex. PyInstaller, à valider).\
**REQ-SEC-005/P1** Mise à jour DB par migrations testées, backup préalable et stratégie rollback/recovery documentée.\
**REQ-SEC-006/P1** Aucune tâche réseau/IA ne doit pouvoir bloquer la gestion locale des états d'ordres et la lecture des diagnostics ; différencier notifications best-effort et contrôles critiques.

## R05-AI2 boundary evidence (2026-11-04)

The optional OpenAI adapter accepts a redacted in-memory secret, pins the official HTTPS endpoint,
disables response storage and sanitizes external failures. No key is read from config, persisted or
logged. Settings can report environment-key presence without revealing its value and can launch one
synthetic request only after explicit model and cost/metadata acknowledgement; the network work runs
outside the Qt event loop. The adapter is still not composed into the scanner runtime, and the first
GUI result remains a human validation gate.

R05-AI3 keeps runtime authorization in memory only. A successful probe enables one explicit Tools
action for the current session; each actual context request still requires a user click. Only
bounded metadata from allowlisted official feeds is sent, the key remains an environment secret,
and the result cannot enter any execution boundary.
