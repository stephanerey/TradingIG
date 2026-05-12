#!/usr/bin/env python3
"""Verify that the Python Codex Operating Pack is installed in the current project."""
from __future__ import annotations

import sys
from pathlib import Path

REQUIRED = [
    "AGENTS.md",
    "DESIGN.md",
    "docs/CURRENT_STATE.md",
    "docs/codex/PROJECT_PROFILE.yaml",
    "docs/codex/SKILL_MAP.md",
    "docs/codex/WORKFLOW_CODEX.md",
    "docs/codex/CODEBASE_MAP.md",
    "docs/codex/REPO_MAP_POLICY.md",
    "docs/codex/TOKEN_OPTIMIZATION.md",
    "docs/codex/tasks/_TEMPLATE/task_plan.md",
    "docs/codex/tasks/_TEMPLATE/findings.md",
    "docs/codex/tasks/_TEMPLATE/progress.md",
    "docs/codex/tasks/_TEMPLATE/decisions.md",
    "docs/codex/tasks/_TEMPLATE/verification.md",
    "docs/adr/ADR_TEMPLATE.md",
    "scripts/codex/generate_python_repo_map.py",
    "scripts/codex/validate_skills.py",
    "scripts/codex/python_token_run.py",
    "scripts/codex/safe_diff_summary.py",
]


def main() -> int:
    missing = [p for p in REQUIRED if not Path(p).exists()]
    if missing:
        print("Missing files:")
        for p in missing:
            print(f"- {p}")
        return 1

    agents_lines = Path("AGENTS.md").read_text(encoding="utf-8").splitlines()
    if len(agents_lines) > 300:
        print(f"WARNING: AGENTS.md is long ({len(agents_lines)} lines). Keep it short.")

    print("OK: Python Codex pack files present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
