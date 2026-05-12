#!/usr/bin/env python3
"""Validate Codex skill folders."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, str] = {}
    current_key = None
    for raw_line in match.group(1).splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("  ") and current_key:
            data[current_key] += " " + line.strip()
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            data[current_key] = value.strip().strip('"').strip("'")
    return data


def validate_skill(path: Path) -> list[str]:
    errors: list[str] = []
    skill_file = path / "SKILL.md"
    if not skill_file.exists():
        return ["missing SKILL.md"]
    text = skill_file.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    name = meta.get("name", "").strip()
    desc = meta.get("description", "").strip()
    if not name:
        errors.append("missing frontmatter name")
    if name and name != path.name:
        errors.append(f"frontmatter name '{name}' != folder '{path.name}'")
    if not desc:
        errors.append("missing frontmatter description")
    if name and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        errors.append("name must be lowercase kebab-case")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Codex skills.")
    parser.add_argument("--path", default=str(Path.home() / ".codex" / "skills"), help="Skills directory")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"ERROR: skills path does not exist: {root}")
        return 2

    skill_dirs = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not skill_dirs:
        print(f"ERROR: no skill directories found in {root}")
        return 1

    total_errors = 0
    for skill_dir in skill_dirs:
        errors = validate_skill(skill_dir)
        if errors:
            total_errors += len(errors)
            print(f"FAIL {skill_dir.name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK   {skill_dir.name}")

    if total_errors:
        print(f"ERROR: {total_errors} validation error(s)")
        return 1
    print("OK: all skills valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
