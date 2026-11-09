# Explicit Paper proposal execution

## Objective

Connect an approved proposal review to the existing local Paper coordinator only after an explicit
operator confirmation, with a fresh atomic risk evaluation.

## Boundaries

- Operator confirmation is mandatory and intent expiry is checked again.
- Reuse the exact proposal fill assumptions and reviewed risk settings.
- The coordinator atomically reevaluates and reserves before local Paper authorization/submission.
- No implicit invocation, IG adapter, DEMO/LIVE order or AUTO path.

## Verification

- Confirmed idempotent Paper opening.
- Missing confirmation, rejected review, expiry and changed-exposure rejection.
- Protected and full offline regressions, Ruff and format checks.
