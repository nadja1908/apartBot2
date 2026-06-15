#!/usr/bin/env python3
# Simple git sync helper: commit any changes and push; optional watch mode.
# Usage:
#   python tools/git_sync.py         # run once
#   python tools/git_sync.py --watch 60  # check every 60s

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def git_exists() -> bool:
    return (ROOT / ".git").exists()


def has_changes() -> bool:
    r = run(["git", "status", "--porcelain"]) 
    return bool(r.stdout.strip())


def current_branch() -> str:
    r = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if r.returncode != 0:
        return "main"
    return r.stdout.strip()


def ensure_repo() -> None:
    if not git_exists():
        print("No git repo found — initializing git repository.")
        r = run(["git", "init"]) 
        if r.returncode != 0:
            print("git init failed:", r.stderr)
            sys.exit(1)
        print("Initialized empty git repository.")


def commit_and_push() -> None:
    ensure_repo()
    if not has_changes():
        print("No changes to commit.")
        return

    # stage everything
    r = run(["git", "add", "-A"], check=True)
    if r.returncode != 0:
        print("git add failed:", r.stderr)
        return

    branch = current_branch()
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    msg = f"chore: auto-sync {ts}"
    r = run(["git", "commit", "-m", msg])
    if r.returncode != 0:
        print("git commit failed or no changes to commit:", r.stderr)
        return
    print(r.stdout.strip())

    # try push
    r = run(["git", "push", "--set-upstream", "origin", branch])
    if r.returncode != 0:
        print("git push failed:")
        print(r.stderr)
        print("If you haven't set a remote, add one and run: git remote add origin <url>")
        return
    print("Pushed to remote.")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--watch", type=int, help="Poll interval in seconds")
    args = p.parse_args(argv)

    if args.watch:
        interval = max(10, args.watch)
        print(f"Watching for changes every {interval}s. Ctrl+C to stop.")
        try:
            while True:
                commit_and_push()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Stopped.")
            return 0
    else:
        commit_and_push()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
