#!/usr/bin/env python3
"""Print a safe compact Git diff summary for Codex review."""
from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout or ""


def main() -> int:
    code, _ = run(["git", "rev-parse", "--is-inside-work-tree"])
    if code != 0:
        print("ERROR: not inside a git repository or git not available")
        return 2

    commands = [
        ["git", "status", "--short"],
        ["git", "diff", "--stat"],
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--stat"],
        ["git", "diff", "--cached", "--name-only"],
    ]
    titles = [
        "## git status --short",
        "## git diff --stat",
        "## git diff --name-only",
        "## git diff --cached --stat",
        "## git diff --cached --name-only",
    ]

    for title, cmd in zip(titles, commands):
        print(title)
        _, out = run(cmd)
        print(out.strip() or "<empty>")
        print()

    print("## Secret check reminders")
    print("- Inspect any .env, credential, token, key, pem, p12, json service account files before commit.")
    print("- Do not paste secrets into Codex output or docs/codex/tasks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
