#!/usr/bin/env python3
"""Run a command, save raw output, print a compact summary."""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path


def compact(lines: list[str], max_lines: int) -> list[str]:
    if len(lines) <= max_lines:
        return lines
    head_n = max_lines // 2
    tail_n = max_lines - head_n
    omitted = len(lines) - head_n - tail_n
    return lines[:head_n] + [f"... <{omitted} line(s) omitted; see raw log> ..."] + lines[-tail_n:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run command and compact output for Codex.")
    parser.add_argument("--max-lines", type=int, default=120)
    parser.add_argument("--log-dir", default=".codex_artifacts/command_logs")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command after --")
    args = parser.parse_args()

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("ERROR: no command provided. Example: python_token_run.py -- pytest -q", file=sys.stderr)
        return 2

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "_".join(part.replace("/", "_").replace("\\", "_") for part in cmd[:4])[:80]
    raw_path = log_dir / f"{stamp}_{safe_name}.log"

    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
    output = proc.stdout or ""
    raw_path.write_text(output, encoding="utf-8", errors="replace")

    lines = output.splitlines()
    print(f"Exit code: {proc.returncode}")
    print(f"Raw log  : {raw_path}")
    print(f"Lines    : {len(lines)}")
    print("--- compact output start ---")
    for line in compact(lines, args.max_lines):
        print(line)
    print("--- compact output end ---")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
