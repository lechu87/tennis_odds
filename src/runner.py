#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

JOBS = [
    ("betclic.py", "logs/betclic.log"),
    ("iforbet_t.py", "logs/iforbet.log"),
    ("etoto_t.py", "logs/etoto.log"),
    ("betfan_t.py", "logs/betfan.log"),
    ("totalbet_t.py", "logs/totalbet.log"),
    ("lvbet_t.py", "logs/lvbet.log"),
]


def run_job(root: Path, script: str, log_rel: str) -> int:
    script_path = root / script
    log_path = root / log_rel

    if not script_path.exists():
        print(f"[WARN] Missing script, skipped: {script}")
        return 0

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n=== RUN {script} ===\n")
        proc = subprocess.run([sys.executable, str(script_path)], stdout=log_file, stderr=log_file)

    if proc.returncode != 0:
        print(f"[ERROR] {script} failed. Check {log_rel}")
    else:
        print(f"[OK] {script}")

    return proc.returncode


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failed = 0

    for script, log_rel in JOBS:
        code = run_job(root, script, log_rel)
        if code != 0:
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
