# Security and Auth

> **PRD Policy:** **PROJECT (editable)** — Fill and update this file for the current project.

**Last updated:** 2026-05-07

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
