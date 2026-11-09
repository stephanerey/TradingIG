# PRD consolidation — task plan

Date: 2026-10-22. Status: complete — documentary consolidation and verification passed.

## Scope and authorization

The user authorized reconstructing the unavailable modular V1.2 pack from the recovered V1.1 archive, then consolidating documentation while preserving local customizations. Target: C:\Projects\TradingIG, branch chore/sr41-upgrade, baseline 512c16d59337d2b92bb475daecb96cc902eb00c0. Initial working tree clean.

## Skills

No specialized skill applied. The legacy Python method skills listed in SKILL_MAP.md are not available in this session; no installation is needed for this Markdown-only consolidation. Planning and diff review are performed directly under AGENTS.md. No Python development, document-office tooling or SR upgrade is in scope.

## Plan

1. Preserve a baseline inventory and recover the V1.1 Markdown sources.
2. Prepare exact proposed files and a conflict/precedence table before application.
3. Reuse F001–F011 and API001–API003; preserve locked templates, images, historical phases and task records.
4. Apply canonical chapter additions, cross-references, new missing feature modules, SR00/R00–R08 phase documents and source provenance.
5. Verify source coverage, identifiers, relative links/anchors, file preservation and documentation-only Git diff.

## Boundaries

Allowed: docs/prd, this task folder and a factual update to docs/CURRENT_STATE.md. No deletion, code/test/config edits, branch creation, commit, installation, dependency changes, application launch, IG call or live activation. SR 4.1 remains a documented future migration requiring its own preview and authorization.

## Verification

Check Git diff --check, existing-file hashes, locked-file invariance, chapter/requirement coverage, Markdown local links and anchors. Application tests are not relevant to a documentation-only change; no runtime validation is claimed.

## Completion

The preview was recorded before applying 61 documentary candidates: 23 new PRD files, 37 modified PRD files and docs/CURRENT_STATE.md. Seven task evidence files accompany the delivery. No deletions, locked-template edits or application changes. See verification.md for actual checks and limitations.

