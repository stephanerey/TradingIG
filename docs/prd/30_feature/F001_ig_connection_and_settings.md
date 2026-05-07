# F001 — IG Connection and Settings

> **PRD Policy:** **PROJECT (editable)** — Feature specification.  
**Last updated:** 2026-05-07


## Goal
Provide a secure configuration screen and connection workflow for IG REST and Streaming APIs.

## Non-goals
- No live order execution in P00.
- No plaintext credential files.

## Requirements
- User can configure IG username, password, API key, environment, and preferred account.
- App can authenticate against IG demo first.
- App displays session/account status.
- App can disconnect and clear session state.
- App masks secrets in UI after entry.
- App supports credential persistence via secure keyring and non-persistence mode.

## Constraints
- Secrets must not be logged, exported, or stored in repository files.
- Live mode must be visibly different from demo mode.

## Acceptance criteria
- Settings can be saved and reloaded without exposing password/API key in settings file.
- Demo login retrieves account metadata.
- Failed login displays a clear error and does not leak secrets.

## Testing notes
- Mock keyring and REST adapter.
- Integration test with demo credentials must be opt-in.
