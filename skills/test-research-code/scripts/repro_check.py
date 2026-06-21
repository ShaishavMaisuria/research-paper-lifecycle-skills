#!/usr/bin/env python3
"""Audit a research-code directory for reproducibility essentials.

Static, read-only audit (Python 3 stdlib only, no network, no execution). It
walks a code directory and reports which artifact-evaluation essentials are
present and which are MISSING, mapped to the things artifact committees and
reproducibility checklists actually look for:

  README                a top-level README (any common form)
  ENV                   a dependency/environment manifest pinned for repro
                        (requirements.txt, environment.yml, pyproject.toml,
                        Pipfile.lock, poetry.lock, setup.py, renv.lock,
                        Dockerfile, ...)
  SEED                  evidence that randomness is seeded for determinism
                        (seed/manual_seed/PYTHONHASHSEED/... in the code)
  ENTRYPOINT            a runnable entrypoint (main guard / Makefile / run.sh /
                        console_scripts / notebook) someone can invoke
  DATA                  instructions or a script for obtaining the data
                        (a data/ dir, a download script, or a README that
                        explains where the data lives)
  RESULTS_CMD           the README states the exact command(s) to reproduce
                        the reported results (the ML Code Completeness item)

This does NOT decide whether a repo *earns* a badge -- it is a checklist of
the prerequisites, so an author can fix gaps before submitting to an artifact
track. Badge interpretation, archival hosting (Zenodo/Software Heritage DOI),
and anonymization are handled in the skill body and references, not here.

Pinning note: the audit reports whether deps are PINNED (==/locked) because
unpinned deps are the most common reason an evaluator cannot rebuild the env.

Usage:
    python3 repro_check.py PATH [--json] [--strict] [--max-files N]

Exit codes:
    0   no MISSING essentials (warnings allowed unless --strict)
    1   one or more MISSING essentials (or any warning with --strict)
    2   usage error (path missing, not a directory, ...)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Static signal tables. Kept as data so they are easy to audit and extend.
# ---------------------------------------------------------------------------

README_NAMES = {
    "readme", "readme.md", "readme.rst", "readme.txt", "readme.org",
    "readme.markdown",
}

# Dependency / environment manifests. value = short human label for the report.
ENV_FILES = {
    "requirements.txt": "pip requirements",
    "requirements-dev.txt": "pip requirements (dev)",
    "environment.yml": "conda environment",
    "environment.yaml": "conda environment",
    "conda.yml": "conda environment",
    "pyproject.toml": "PEP 621 / poetry project",
    "setup.py": "setuptools",
    "setup.cfg": "setuptools",
    "pipfile": "pipenv",
    "pipfile.lock": "pipenv lockfile (pinned)",
    "poetry.lock": "poetry lockfile (pinned)",
    "renv.lock": "R renv lockfile (pinned)",
    "spack.yaml": "spack environment",
    "dockerfile": "Docker image recipe",
    "containerfile": "OCI image recipe",
    "package.json": "node package manifest",
    "package-lock.json": "node lockfile (pinned)",
    "go.mod": "go module",
    "cargo.toml": "rust crate",
    "cargo.lock": "rust lockfile (pinned)",
    "uv.lock": "uv lockfile (pinned)",
}
# Files whose mere presence implies pinned/locked deps.
LOCKFILES = {
    "pipfile.lock", "poetry.lock", "renv.lock", "package-lock.json",
    "cargo.lock", "uv.lock",
}

# Entrypoint files (presence is enough).
ENTRYPOINT_FILES = {
    "makefile", "run.sh", "run.py", "main.py", "train.py", "evaluate.py",
    "eval.py", "reproduce.sh", "reproduce.py", "repro.sh", "experiment.py",
    "justfile", "dvc.yaml", "snakefile",
}

# Source extensions to scan for in-code signals (seed, main guard).
SOURCE_EXTS = {".py", ".sh", ".r", ".jl", ".lua", ".ipynb"}

# Directories we never descend into.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".mypy_cache", ".pytest_cache", ".ipynb_checkpoints",
    ".tox", "build", "dist", ".eggs", ".idea", ".vscode",
}

# In-code seeding signals (case-insensitive). One hit is enough.
SEED_PATTERNS = [
    r"\brandom\.seed\s*\(",
    r"\bnp\.random\.seed\s*\(",
    r"\bnumpy\.random\.seed\s*\(",
    r"\bnp\.random\.default_rng\s*\(",
    r"\b(?:torch|tf)\.(?:random\.)?(?:manual_)?set_seed\s*\(",
    r"\btorch\.manual_seed\s*\(",
    r"\btorch\.cuda\.manual_seed(?:_all)?\s*\(",
    r"\bset_seed\s*\(",
    r"\bseed_everything\s*\(",
    r"\bpl\.seed_everything\s*\(",
    r"\bPYTHONHASHSEED\b",
    r"\bset\.seed\s*\(",            # R
    r"\bRandom\.seed!\s*\(",        # Julia
    r"\btf\.keras\.utils\.set_random_seed\s*\(",
    r"\bdeterministic\s*=\s*True",  # torch.use_deterministic / cudnn
]
SEED_RE = re.compile("|".join(SEED_PATTERNS), re.IGNORECASE)

# Test signals -- not a required essential, but reported (smoke test presence).
TEST_DIR_NAMES = {"test", "tests"}
TEST_FILE_RE = re.compile(r"(^test_.*\.py$)|(.*_test\.py$)|(^test.*\.sh$)", re.I)

# README content cues.
DATA_README_RE = re.compile(
    r"\b(download|dataset|data\s*set|wget|curl|kaggle|huggingface|hf\s+hub|"
    r"zenodo|figshare|dryad|s3://|gs://|gdown|google\s+drive|obtain\s+the\s+data)\b",
    re.IGNORECASE,
)
RESULTS_CMD_RE = re.compile(
    r"(reproduce|to\s+reproduce|reproduc\w*\s+the\s+results|"
    r"```[\s\S]*?(python|bash|sh|make|\./|docker\s+run|conda\s+run)[\s\S]*?```|"
    r"^\s*\$\s+\S+|^\s*(python|bash|sh|make|\./run|docker)\b)",
    re.IGNORECASE | re.MULTILINE,
)
DATA_DIR_NAMES = {"data", "datasets", "dataset"}
DATA_SCRIPT_RE = re.compile(
    r"(download|fetch|get|prepare).*data|data.*(download|fetch|prepare)", re.I
)

MAIN_GUARD_RE = re.compile(r"if\s+__name__\s*==\s*['\"]__main__['\"]")
CONSOLE_SCRIPTS_RE = re.compile(r"console_scripts|\[project\.scripts\]|entry_points")


def fail(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


class Audit:
    def __init__(self) -> None:
        self.readme: Path | None = None
        self.readme_text: str = ""
        self.env: list[tuple[str, str]] = []      # (rel-path, label)
        self.pinned: bool = False
        self.entrypoints: list[str] = []
        self.seed_hits: list[str] = []            # rel-paths with a seed signal
        self.has_main_guard: bool = False
        self.has_console_scripts: bool = False
        self.data_dir: bool = False
        self.data_script: list[str] = []
        self.data_in_readme: bool = False
        self.results_cmd_in_readme: bool = False
        self.test_dirs: list[str] = []
        self.test_files: list[str] = []
        self.n_source_files: int = 0
        self.scanned_files: int = 0
        self.truncated: bool = False


def walk(root: Path, max_files: int) -> Audit:
    a = Audit()
    for path in sorted(root.rglob("*")):
        # Prune skip dirs cheaply by checking any path part.
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            name = path.name.lower()
            if name in TEST_DIR_NAMES:
                a.test_dirs.append(rel)
            if name in DATA_DIR_NAMES:
                a.data_dir = True
            continue
        if not path.is_file():
            continue

        name = path.name.lower()

        # README (top-level preferred, but accept nested as a weaker hit).
        if name in README_NAMES and a.readme is None:
            a.readme = path
            try:
                a.readme_text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                a.readme_text = ""

        if name in ENV_FILES:
            a.env.append((rel, ENV_FILES[name]))
            if name in LOCKFILES:
                a.pinned = True

        if name in ENTRYPOINT_FILES:
            a.entrypoints.append(rel)

        if TEST_FILE_RE.match(path.name):
            a.test_files.append(rel)

        if DATA_SCRIPT_RE.search(name):
            a.data_script.append(rel)

        ext = path.suffix.lower()
        if ext in SOURCE_EXTS:
            a.n_source_files += 1
            if a.scanned_files < max_files:
                a.scanned_files += 1
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if SEED_RE.search(text):
                    a.seed_hits.append(rel)
                if MAIN_GUARD_RE.search(text):
                    a.has_main_guard = True
                if CONSOLE_SCRIPTS_RE.search(text):
                    a.has_console_scripts = True
            else:
                a.truncated = True

    # Pinned also if any requirements file actually pins (== or @ or url).
    if not a.pinned:
        for rel, _label in a.env:
            p = root / rel
            if p.name.lower().startswith("requirements") and p.suffix == ".txt":
                try:
                    body = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if re.search(r"(==|@|https?://|git\+)", body):
                    a.pinned = True
                    break

    if a.readme_text:
        a.data_in_readme = bool(DATA_README_RE.search(a.readme_text))
        a.results_cmd_in_readme = bool(RESULTS_CMD_RE.search(a.readme_text))

    return a


def evaluate(a: Audit) -> list[tuple[str, str, str]]:
    """Return list of (essential, status, detail). status in OK/MISSING/WARN."""
    out: list[tuple[str, str, str]] = []

    # README
    if a.readme is not None:
        out.append(("README", "OK", f"found {a.readme.name}"))
    else:
        out.append(("README", "MISSING",
                    "no README found -- evaluators need a top-level README "
                    "describing what the artifact is and how to run it"))

    # ENV
    if a.env:
        labels = ", ".join(sorted({lbl for _r, lbl in a.env}))
        pin = "pinned" if a.pinned else "NOT pinned"
        sev = "OK" if a.pinned else "WARN"
        detail = f"{labels} ({pin})"
        if not a.pinned:
            detail += (" -- pin exact versions (==) or add a lockfile; unpinned "
                       "deps are the #1 reason an env cannot be rebuilt")
        out.append(("ENV", sev, detail))
    else:
        out.append(("ENV", "MISSING",
                    "no dependency/environment manifest (requirements.txt, "
                    "environment.yml, pyproject.toml, Dockerfile, ...) -- "
                    "evaluators cannot recreate the runtime"))

    # SEED
    if a.seed_hits:
        out.append(("SEED", "OK",
                    f"seeding found in {len(a.seed_hits)} file(s), "
                    f"e.g. {a.seed_hits[0]}"))
    else:
        out.append(("SEED", "MISSING",
                    "no seed-setting found (random.seed / torch.manual_seed / "
                    "PYTHONHASHSEED / set.seed ...) -- without fixed seeds runs "
                    "are nondeterministic and results won't match"))

    # ENTRYPOINT
    ep_bits = list(a.entrypoints)
    if a.has_main_guard:
        ep_bits.append("__main__ guard")
    if a.has_console_scripts:
        ep_bits.append("console_scripts/entry_points")
    if ep_bits:
        out.append(("ENTRYPOINT", "OK", ", ".join(ep_bits[:4])
                    + (" ..." if len(ep_bits) > 4 else "")))
    else:
        out.append(("ENTRYPOINT", "MISSING",
                    "no obvious entrypoint (Makefile / run.sh / main.py / "
                    "__main__ guard / console_scripts) -- give evaluators one "
                    "command that runs the artifact end to end"))

    # DATA
    data_bits = []
    if a.data_dir:
        data_bits.append("data/ directory")
    if a.data_script:
        data_bits.append(f"data script ({a.data_script[0]})")
    if a.data_in_readme:
        data_bits.append("README data instructions")
    if data_bits:
        out.append(("DATA", "OK", ", ".join(data_bits)))
    else:
        out.append(("DATA", "MISSING",
                    "no data instructions (no data/ dir, no download script, "
                    "README does not say where the data lives) -- state how to "
                    "obtain inputs, or note 'no external data'"))

    # RESULTS_CMD
    if a.results_cmd_in_readme:
        out.append(("RESULTS_CMD", "OK",
                    "README shows command(s) to run / reproduce"))
    elif a.readme is None:
        out.append(("RESULTS_CMD", "MISSING",
                    "no README, so no reproduce command -- the ML Code "
                    "Completeness checklist wants the exact command per result"))
    else:
        out.append(("RESULTS_CMD", "WARN",
                    "README has no recognizable run/reproduce command block -- "
                    "add the exact command(s) that reproduce each reported "
                    "result (a table of results + its command)"))

    return out


def report_text(root: Path, a: Audit, rows: list[tuple[str, str, str]]) -> str:
    lines = [f"repro_check: {root}"]
    n_src = a.n_source_files
    note = f"  scanned {a.scanned_files}/{n_src} source files for in-code signals"
    if a.truncated:
        note += " (truncated; raise --max-files for full coverage)"
    lines.append(note)
    if a.test_dirs or a.test_files:
        nt = len(a.test_files)
        td = ", ".join(a.test_dirs) if a.test_dirs else ""
        lines.append(f"  tests present: {nt} test file(s)"
                     + (f"; dir(s): {td}" if td else ""))
    else:
        lines.append("  tests present: none found -- add a smoke/sanity test "
                     "(see the skill for a minimal template)")
    lines.append("")
    width = max(len(name) for name, _s, _d in rows)
    for name, status, detail in rows:
        lines.append(f"  [{status:>7}] {name.ljust(width)}  {detail}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("path", help="path to the research-code directory to audit")
    p.add_argument("--json", action="store_true",
                   help="emit a machine-readable JSON report instead of text")
    p.add_argument("--strict", action="store_true",
                   help="treat WARN findings as failures (exit 1)")
    p.add_argument("--max-files", type=int, default=2000, metavar="N",
                   help="max source files to scan for in-code signals "
                        "(default 2000; guards against huge repos)")
    args = p.parse_args()

    root = Path(args.path)
    if not root.exists():
        fail(f"path not found: {args.path}")
    if not root.is_dir():
        fail(f"not a directory: {args.path} (point at the code dir, not a file)")
    if args.max_files < 1:
        fail("--max-files must be >= 1")

    a = walk(root, args.max_files)
    rows = evaluate(a)

    missing = [r for r in rows if r[1] == "MISSING"]
    warns = [r for r in rows if r[1] == "WARN"]

    if args.json:
        payload = {
            "path": str(root),
            "essentials": [
                {"name": n, "status": s, "detail": d} for n, s, d in rows
            ],
            "tests_present": bool(a.test_dirs or a.test_files),
            "test_files": a.test_files,
            "deps_pinned": a.pinned,
            "summary": {
                "missing": [r[0] for r in missing],
                "warn": [r[0] for r in warns],
                "ok": [r[0] for r in rows if r[1] == "OK"],
            },
            "scanned_files": a.scanned_files,
            "source_files": a.n_source_files,
            "truncated": a.truncated,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(report_text(root, a, rows))
        if missing:
            print(f"\nRESULT: {len(missing)} MISSING essential(s): "
                  + ", ".join(r[0] for r in missing))
        elif warns:
            print(f"\nRESULT: all essentials present, {len(warns)} warning(s)")
        else:
            print("\nRESULT: all reproducibility essentials present")
        print("NOTE: a passing checklist is necessary, not sufficient -- it does "
              "NOT mean the artifact earns a badge. Verify the venue's current "
              "Call for Artifacts and that results reproduce within tolerance.")

    if missing or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
