# Findings

- The 41 local PRD ZIP downloads have identical SHA-256 E5D724BE71398269AA92E0FE48857758D03868786A25EF6CD40E1339D3E00F6B and contain V1.1, not the unavailable original V1.2.
- The user explicitly authorized reconstruction from that V1.1 on 2026-10-22.
- Existing PRD: 100 files, 94 Markdown, six images; 41 LOCKED, 50 PROJECT and three unmarked Markdown documents.
- Git baseline is clean at 512c16d59337d2b92bb475daecb96cc902eb00c0 on chore/sr41-upgrade.
- PRD and task board still describe initial bootstrap; code already includes MainWindow, CandleAggregationService and IG adapters. Do not infer completion of historical TODOs from class existence.
- CURRENT_STATE.md and human RepoMap remain largely placeholders. Generated RepoMap describes the existing Python/PyQt layout; application verification is outside this task.
- LiveTradingDisabledError is present in real-order adapter methods; preserve these files unchanged.
- Existing English-only templates, Pxx phases, broad override wording, state-machine vocabulary and V2 timing need explicit reconciliation with the French V1.1 requirements.
- The archived audit has an older R07 live-oriented roadmap. The PRD chapter 18 SR00/R00–R08 sequence takes precedence for the reconstructed roadmap.

## Consolidation findings

- All 24 chapters, 125 explicitly defined REQ identifiers and 38 AC identifiers from V1.1 are covered in the reconstructed modular PRD.
- The source itself disagrees on strategy/market settings inheritance (REQ-RISK-010 versus REQ-UI-005). This is explicitly open, recorded as T-1002, and blocks dependent R03/R04 implementation rather than documentary delivery.
- Source §18 uses BUG-DATA-003 for the GUI I/O finding named BUG-UI-003 in §3; an erratum records the alias.
- Source hard-break trailing spaces initially triggered Git whitespace diagnostics. They were normalized to Markdown backslash hard breaks without changing requirement wording; final Git and new-file whitespace checks pass.

