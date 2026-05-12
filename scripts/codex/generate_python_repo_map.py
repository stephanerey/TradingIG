#!/usr/bin/env python3
"""Generate a compact Python-focused repository map for Codex."""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import os
import sys
from pathlib import Path
from typing import Iterable

IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox",
    "build", "dist", "site-packages", "node_modules", ".idea", ".vscode",
    "htmlcov", ".coverage", "output", "outputs", "logs", ".codex_backups",
    ".codex_artifacts",
}

PY_LIMIT = 500
AST_FILE_SIZE_LIMIT = 250_000


def is_ignored(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_files(root: Path, suffixes: tuple[str, ...]) -> Iterable[Path]:
    for p in root.rglob("*"):
        if is_ignored(p.relative_to(root)):
            continue
        if p.is_file() and p.name.endswith(suffixes):
            yield p


def read_pyproject(root: Path) -> dict:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    try:
        import tomllib
        return tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": str(exc)}


def extract_symbols(path: Path) -> tuple[list[str], list[str], list[str]]:
    if path.stat().st_size > AST_FILE_SIZE_LIMIT:
        return [], [], ["SKIPPED_AST_FILE_TOO_LARGE"]
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        return [], [], [f"SYNTAX_ERROR line {exc.lineno}"]
    except Exception as exc:
        return [], [], [f"READ_ERROR {type(exc).__name__}"]

    classes: list[str] = []
    funcs: list[str] = []
    notes: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(node.name)
    return classes[:12], funcs[:20], notes


def categorize_python_files(root: Path, py_files: list[Path]) -> dict[str, list[Path]]:
    categories = {
        "package_src": [],
        "tests": [],
        "scripts": [],
        "gui": [],
        "hardware_io": [],
        "data_ml": [],
        "other_python": [],
    }
    for p in py_files:
        r = rel(p, root)
        low = r.lower()
        parts = p.relative_to(root).parts
        if parts and parts[0] == "tests" or "/test_" in low or low.endswith("_test.py"):
            categories["tests"].append(p)
        elif parts and parts[0] == "scripts":
            categories["scripts"].append(p)
        elif any(k in low for k in ("qt", "pyqt", "pyside", "gui", "widget", "window", "dialog", "view")):
            categories["gui"].append(p)
        elif any(k in low for k in ("modbus", "serial", "tcp", "socket", "visa", "sdr", "instrument", "driver", "hardware", "axis", "motor")):
            categories["hardware_io"].append(p)
        elif any(k in low for k in ("pandas", "data", "dataset", "csv", "parquet", "numpy", "model", "train", "indicator", "feature")):
            categories["data_ml"].append(p)
        elif parts and parts[0] == "src":
            categories["package_src"].append(p)
        else:
            categories["other_python"].append(p)
    return categories


def section_files(title: str, files: list[Path], root: Path, include_symbols: bool = True) -> list[str]:
    lines = [f"## {title}", ""]
    if not files:
        return lines + ["- _none detected_", ""]
    for p in files[:PY_LIMIT]:
        item = f"- `{rel(p, root)}`"
        if include_symbols:
            classes, funcs, notes = extract_symbols(p)
            extras = []
            if classes:
                extras.append("classes: " + ", ".join(classes[:8]))
            if funcs:
                extras.append("funcs: " + ", ".join(funcs[:10]))
            if notes:
                extras.append("notes: " + ", ".join(notes))
            if extras:
                item += " — " + " | ".join(extras)
        lines.append(item)
    if len(files) > PY_LIMIT:
        lines.append(f"- ... truncated, {len(files) - PY_LIMIT} more file(s)")
    lines.append("")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Python codebase map.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--write", action="store_true", help="Write docs/codex/CODEBASE_MAP.generated.md")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    pyproject = read_pyproject(root)
    py_files = sorted(iter_files(root, (".py",)))
    categories = categorize_python_files(root, py_files)

    config_files = []
    for name in (
        "pyproject.toml", "setup.cfg", "setup.py", "requirements.txt", "requirements-dev.txt",
        "tox.ini", "noxfile.py", "pytest.ini", ".python-version", "ruff.toml", "mypy.ini",
        "pyrightconfig.json", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ):
        p = root / name
        if p.exists():
            config_files.append(p)

    resources = sorted(
        list(iter_files(root, (".ui", ".qrc", ".qss", ".yaml", ".yml", ".json", ".toml", ".ini")))
    )[:200]

    lines: list[str] = [
        "# CODEBASE_MAP.generated.md",
        "",
        "> Généré automatiquement. Ne pas éditer manuellement.",
        f"> Date: {dt.datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Project metadata",
        "",
        f"- Root: `{root}`",
        f"- Python files: {len(py_files)}",
    ]

    if pyproject:
        if "_error" in pyproject:
            lines.append(f"- pyproject.toml parse error: `{pyproject['_error']}`")
        else:
            project = pyproject.get("project", {})
            lines.append(f"- Project name: `{project.get('name', 'unknown')}`")
            lines.append(f"- Requires Python: `{project.get('requires-python', 'not specified')}`")
            scripts = project.get("scripts", {})
            if scripts:
                lines.append("- Entry points:")
                for name, target in scripts.items():
                    lines.append(f"  - `{name}` -> `{target}`")
    lines.append("")

    lines += section_files("Package/source Python files", categories["package_src"], root)
    lines += section_files("GUI-related Python candidates", categories["gui"], root)
    lines += section_files("Hardware / I/O Python candidates", categories["hardware_io"], root)
    lines += section_files("Data / ML Python candidates", categories["data_ml"], root)
    lines += section_files("Scripts", categories["scripts"], root)
    lines += section_files("Tests", categories["tests"], root)
    lines += section_files("Other Python files", categories["other_python"], root)
    lines += section_files("Config/runtime files", config_files, root, include_symbols=False)
    lines += section_files("Resource/config candidates", resources, root, include_symbols=False)

    text = "\n".join(lines).rstrip() + "\n"
    target = root / "docs" / "codex" / "CODEBASE_MAP.generated.md"
    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
