#!/usr/bin/env python3
"""Audit an artifact repository for reproducibility completeness.

Inventories a code/artifact directory against the ML Code Completeness
Checklist (paperswithcode, 5 items) and flags missing reproduction steps and
archival-hosting gaps. It reads files; it RUNS NOTHING. Heavy/long commands are
left for the author to run in their own sandbox.

Checks (advisory — verify each against the venue's current Call for Artifacts):
  1. dependencies      requirements.txt / environment.yml / pyproject / setup.py / Dockerfile
  2. training code     a train/fit entrypoint (heuristic: train.py, *train*, "def train")
  3. evaluation code   an eval/test entrypoint (eval.py, test*, "def evaluate")
  4. pretrained models a weights/checkpoint dir or a documented download
  5. README w/ results a README that contains BOTH a results table AND a runnable command
Plus:
  - tests present      a tests/ dir or test_*.py (the artifact's OWN tests, which the author runs)
  - run commands       how-to-reproduce commands are documented (so the author can run them)
  - archival hosting   README points only to a GitHub/personal URL (Artifacts-Available
                       badge needs an archival DOI: Zenodo/FigShare/Dryad/Software Heritage)
  - anonymity leaks    when --blind double, scan for author names / non-anon repo URLs / emails

Usage:
    python3 audit_repo.py path/to/artifact-repo [--blind single|double] [--json]

Exit codes: 0 no ERROR, 1 ERROR (a missing-essential gap or anonymity leak),
2 usage/path failure. --strict makes WARNs fail too.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import verifylib as vl

_SKIP_DIRS = {".git", ".hg", "node_modules", "__pycache__", ".venv", "venv",
              ".mypy_cache", ".pytest_cache", "site-packages", ".idea"}

_DEP_FILES = ("requirements.txt", "environment.yml", "environment.yaml",
              "pyproject.toml", "setup.py", "setup.cfg", "Pipfile",
              "poetry.lock", "Dockerfile", "conda.yaml")
_WEIGHT_EXT = (".pt", ".pth", ".ckpt", ".h5", ".pb", ".onnx", ".safetensors",
               ".bin", ".npz", ".weights")
_WEIGHT_DIRS = ("checkpoints", "checkpoint", "ckpt", "weights", "models",
                "pretrained", "saved_models")
_README_NAMES = ("readme.md", "readme.rst", "readme.txt", "readme")

# command-ish lines in a README (the reproduce recipe)
_CMD_RE = re.compile(
    r"(?m)^\s*\$?\s*(python3?|bash|sh|make|docker|conda|pip|torchrun|"
    r"accelerate|sbatch|\./)\b"
)
# a markdown table row that looks like a results table (has | and a digit)
_TABLE_ROW_RE = re.compile(r"(?m)^\s*\|.*\d.*\|")

_GITHUB_RE = re.compile(r"https?://(?:www\.)?(github\.com|gitlab\.com|bitbucket\.org)/[\w.\-/]+",
                        re.I)
_ARCHIVAL_RE = re.compile(
    r"(zenodo\.org|doi\.org|figshare\.com|datadryad\.org|dryad|"
    r"softwareheritage\.org|swh:1:|osf\.io|/record/\d+|10\.\d{4,9}/)", re.I)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_ANON_HOST_RE = re.compile(r"anonymous\.4open\.science|anonymous", re.I)


def _walk(root: pathlib.Path):
    for p in root.rglob("*"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        yield p


def _read(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def collect(root: pathlib.Path, *, blind: str) -> tuple[list[vl.Finding], list[str]]:
    findings: list[vl.Finding] = []
    notes: list[str] = []
    files = [p for p in _walk(root) if p.is_file()]
    rel = lambda p: str(p.relative_to(root))
    names_lower = {p.name.lower() for p in files}
    all_text_names = {rel(p).lower() for p in files}

    # 1. dependencies
    deps = [rel(p) for p in files if p.name in _DEP_FILES]
    if deps:
        findings.append(vl.Finding("INFO", "checklist/dependencies",
                                   deps[0], f"dependency spec present ({', '.join(deps[:3])})"))
    else:
        findings.append(vl.Finding("ERROR", "checklist/dependencies", rel(root),
                                   "no requirements.txt/environment.yml/pyproject/"
                                   "setup.py/Dockerfile — a clean run cannot pin deps"))

    # 2 & 3. training / evaluation code (heuristic; report, do not over-claim)
    py = [p for p in files if p.suffix == ".py"]
    is_test = lambda p: (p.name.startswith("test_") or p.name.endswith("_test.py")
                         or "tests" in [x.lower() for x in p.parts])
    non_test_py = [p for p in py if not is_test(p)]
    train_hit = [rel(p) for p in non_test_py if "train" in p.name.lower()]
    # an evaluation entrypoint, but never the unit-test files (those are item 6)
    eval_hit = [rel(p) for p in non_test_py
                if re.search(r"eval|infer|predict|score", p.name.lower())]
    # fall back to scanning for def train / def evaluate (skip test files)
    if not train_hit:
        train_hit = [rel(p) for p in non_test_py
                     if re.search(r"def\s+train\b|def\s+fit\b", _read(p))][:1]
    if not eval_hit:
        eval_hit = [rel(p) for p in non_test_py
                    if re.search(r"def\s+(evaluate|eval|predict)\b", _read(p))][:1]
    if train_hit:
        findings.append(vl.Finding("INFO", "checklist/training-code", train_hit[0],
                                   "training entrypoint found (heuristic)"))
    else:
        findings.append(vl.Finding("WARN", "checklist/training-code", rel(root),
                                   "no obvious training entrypoint — fine if the "
                                   "artifact ships trained models, else flag missing"))
    if eval_hit:
        findings.append(vl.Finding("INFO", "checklist/eval-code", eval_hit[0],
                                   "evaluation/inference entrypoint found (heuristic)"))
    else:
        findings.append(vl.Finding("WARN", "checklist/eval-code", rel(root),
                                   "no obvious evaluation entrypoint — needed to "
                                   "regenerate the paper's reported metrics"))

    # 4. pretrained models
    weight_files = [rel(p) for p in files if p.suffix.lower() in _WEIGHT_EXT]
    weight_dirs = [rel(p) for p in files
                   if any(d in [x.lower() for x in p.parts] for d in _WEIGHT_DIRS)]
    if weight_files or weight_dirs:
        findings.append(vl.Finding("INFO", "checklist/pretrained", (weight_files or weight_dirs)[0],
                                   "model weights / checkpoint location present"))
    else:
        findings.append(vl.Finding("INFO", "checklist/pretrained", rel(root),
                                   "no checkpoint files in-tree — OK if README "
                                   "documents a download, else reproduction "
                                   "requires full (re)training"))

    # README + items 5 (results table + command), tests, hosting
    readmes = [p for p in files if p.name.lower() in _README_NAMES]
    if not readmes:
        findings.append(vl.Finding("ERROR", "checklist/readme", rel(root),
                                   "no README — the checklist requires a README "
                                   "with a results table and the exact reproduce command"))
    for rp in readmes:
        txt = _read(rp)
        has_table = bool(_TABLE_ROW_RE.search(txt))
        has_cmd = bool(_CMD_RE.search(txt))
        if not has_table:
            findings.append(vl.Finding("WARN", "readme/results-table", rel(rp),
                                       "README has no results table — checklist item 5 "
                                       "wants a table mapping each number to its command"))
        if not has_cmd:
            findings.append(vl.Finding("ERROR", "readme/run-command", rel(rp),
                                       "README documents no runnable command — the "
                                       "author cannot follow a reproduce recipe"))
        else:
            findings.append(vl.Finding("INFO", "readme/run-command", rel(rp),
                                       "reproduce command(s) documented"))
        # hosting: GitHub-only vs archival DOI
        gh = _GITHUB_RE.search(txt)
        arch = _ARCHIVAL_RE.search(txt)
        if gh and not arch:
            findings.append(vl.Finding("WARN", "hosting/archival-doi", rel(rp),
                                       "only a GitHub/GitLab URL found; the "
                                       "Artifacts-Available badge needs an ARCHIVAL "
                                       "DOI (Zenodo/FigShare/Dryad/Software Heritage). "
                                       "Re-check the venue's current Call for Artifacts."))
        elif arch:
            findings.append(vl.Finding("INFO", "hosting/archival-doi", rel(rp),
                                       "archival identifier (DOI/SWHID) referenced"))

    # tests (the artifact's OWN tests — the author runs them)
    test_dirs = [rel(p) for p in files if "tests" in [x.lower() for x in p.parts]]
    test_files = [rel(p) for p in py
                  if p.name.startswith("test_") or p.name.endswith("_test.py")]
    if test_dirs or test_files:
        findings.append(vl.Finding("INFO", "tests/present",
                                   (test_dirs or test_files)[0],
                                   f"artifact tests present ({len(set(test_dirs) | set(test_files))} "
                                   "path(s)) — author should run them in the sandbox"))
    else:
        findings.append(vl.Finding("WARN", "tests/present", rel(root),
                                   "no tests/ dir or test_*.py — no self-check that "
                                   "the artifact runs before metric comparison"))

    # double-blind anonymity scan over README/repo text
    if blind == "double":
        for rp in readmes:
            txt = _read(rp)
            for m in set(_EMAIL_RE.findall(txt)):
                findings.append(vl.Finding("ERROR", "anon/email", rel(rp),
                                           f"email address leaks identity: {m}"))
            gh = _GITHUB_RE.search(txt)
            if gh and not _ANON_HOST_RE.search(gh.group(0)):
                findings.append(vl.Finding("ERROR", "anon/repo-url", rel(rp),
                                           f"de-anonymizing repo URL: {gh.group(0)} "
                                           "— use anonymous.4open.science or an "
                                           "anonymized ZIP for review"))
        notes.append("double-blind scan covered README text only; also check "
                     "LICENSE/AUTHORS, code comments, commit history, and "
                     "config files for names before submitting")
    else:
        notes.append("single-blind/non-blind: anonymity scan skipped "
                     "(pass --blind double to enable)")

    notes.append(f"inventoried {len(files)} file(s) under {root} — nothing was "
                 "executed; run training/eval/tests yourself in a sandbox")
    return findings, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", help="path to the artifact repository (a directory)")
    ap.add_argument("--blind", choices=("single", "double", "none"),
                    default="none", help="review blinding (double enables anon scan)")
    vl.add_common_args(ap)
    args = ap.parse_args()

    root = pathlib.Path(args.repo)
    if not root.exists() or not root.is_dir():
        print(f"error: artifact repo not found or not a directory: {args.repo}",
              file=sys.stderr)
        return 2

    findings, notes = collect(root, blind=args.blind)
    return vl.report("audit_repo", findings, notes, args, extra={"repo": str(root)})


if __name__ == "__main__":
    sys.exit(main())
