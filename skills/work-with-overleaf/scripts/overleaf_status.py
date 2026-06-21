#!/usr/bin/env python3
"""Inspect a local copy of an Overleaf project and print the safe round-trip steps.

Stdlib only. Read-only: it inspects git state via `git` and reports; it never
pushes, pulls, or writes. Detects whether a directory is an Overleaf Git clone
(remote host git.overleaf.com) or a GitHub-synced/plain copy, reports uncommitted
changes, and prints the exact, confirm-first sync commands — with the access
token redacted if it appears in a remote URL.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

TOKEN_RE = re.compile(r"https://[^@/]*@")  # strip any user:token@ in a remote URL


def git(args, cwd):
    try:
        out = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                             text=True, timeout=15)
        return out.returncode, out.stdout.strip(), out.stderr.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)


def redact(url: str) -> str:
    return TOKEN_RE.sub("https://", url)


def main() -> int:
    ap = argparse.ArgumentParser(description="Report Overleaf project sync state and safe round-trip steps (read-only).")
    ap.add_argument("path", nargs="?", default=".", help="local project directory (default: .)")
    args = ap.parse_args()
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"ERROR not a directory: {root}", file=sys.stderr)
        return 1

    rc, _, _ = git(["rev-parse", "--is-inside-work-tree"], root)
    is_git = rc == 0
    tex = list(root.glob("*.tex")) + list(root.glob("**/main.tex"))[:1]
    print(f"Overleaf project check — {root}")
    print(f"  .tex found: {'yes (' + tex[0].name + ')' if tex else 'NO — is this the project root?'}")

    if not is_git:
        print("  git: not a git repo → this looks like a ZIP download.")
        print("  Round-trip: edit locally, then in Overleaf use Menu → Upload to")
        print("  replace changed files (no auto-merge). Confirm each file with the author.")
        return 0

    rc, remote, _ = git(["remote", "get-url", "origin"], root)
    remote = redact(remote) if rc == 0 else "(no origin remote)"
    overleaf = "git.overleaf.com" in remote
    rc, branch, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    rc, status, _ = git(["status", "--porcelain"], root)
    dirty = bool(status)

    print(f"  remote: {remote}")
    print(f"  kind: {'Overleaf Git integration' if overleaf else 'GitHub sync or plain git'}")
    print(f"  branch: {branch}  (Overleaf uses 'main'; older clones 'master')")
    print(f"  uncommitted changes: {'YES' if dirty else 'none'}")
    print("\nSafe round-trip (confirm with the author before any push):")
    print("  1. git pull --rebase        # get collaborators' latest first")
    if dirty:
        print("  2. review the diff, then: git add -A && git commit -m '...'")
    print(f"  3. git push origin {branch or 'main'}   # only after review")
    print("\nNever force-push or rewrite history — co-authors may be editing on Overleaf.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
