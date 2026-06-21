#!/usr/bin/env python3
"""Static release-refactor audit for a research-code directory.

Read-only (Python 3 stdlib only; no network, no execution, no writes). It walks
a code directory and reports release-refactor *opportunities* an author should
address before publishing the code, and -- this is the point of the script --
it classifies every finding by RESULT-RISK:

  safe          a mechanical, behavior-preserving cleanup (rename a file, add a
                README, write a .gitignore, move a script into a folder). Doing
                it cannot change the numbers the paper reports.

  behavior-risk a change that COULD alter results if done carelessly -- e.g.
                deleting a code path that might still be reachable, removing a
                hardcoded constant, touching seeding/threading/dtype, dropping a
                file that an experiment imports. The skill must ASK the author
                before touching anything in this class (copilot, not pilot).

  identity      a double-blind leak (author name/email/institution/home path /
                .git history) that must be scrubbed before a blind-review upload.
                Hand the deep sweep to anonymize-paper; this only flags surface.

The audit is intentionally conservative: when in doubt it labels a finding
behavior-risk rather than safe, because the whole contract of a release refactor
is "clean the repo WITHOUT changing what it computes."

This script does NOT refactor anything, does NOT decide a paper reproduces, and
does NOT replace anonymize-paper / test-research-code / prepare-artifacts. It is
the external, measurable signal the skill's plan is grounded in.

Categories reported (each finding carries a category + risk + file[:line]):

  dead-code     commented-out blocks, `if False:` / `if 0:` guards, unreachable
                experiment branches, *.bak / *.old / *_v2 / *_copy / *_final
                files, .ipynb_checkpoints  -- candidates to remove (behavior-risk:
                confirm nothing imports/uses them first).
  config        magic numbers / hardcoded hyperparameters / absolute paths
                embedded in source that should move to a config file or CLI
                flag (behavior-risk to extract: the value must be preserved
                exactly).
  entrypoint    whether there is one obvious documented way to run the pipeline
                (Makefile / run.sh / __main__ / console_scripts) and a README
                that names it (safe to add docs; entrypoint wiring is structural).
  layout        repo-structure hygiene: a README, a LICENSE, a .gitignore, a
                src/ or package dir vs a flat dump of scripts, a results/output
                dir mixed into source (mostly safe to add/move).
  determinism   seeding present? nondeterminism smells (unseeded RNG, time-based
                seeds, set/dict ordering used as data, multi-thread/worker
                without a fixed order) -- behavior-risk: changing these changes
                results, so flag and DISCUSS, never silently "fix".
  identity      surface double-blind leaks (see above).
  hygiene       junk that bloats a release: __pycache__, *.pyc, large data/model
                blobs committed in-tree, .DS_Store, editor swap files (safe to
                gitignore/remove from the release copy).

Usage:
    python3 release_audit.py PATH [--blind {none,single,double}]
                                  [--names "Jane Doe,Example University"]
                                  [--json] [--strict] [--max-files N]
                                  [--max-bytes N]

Exit codes:
    0   no behavior-risk and no identity findings (safe/hygiene/info only);
        with --strict, also requires zero findings at all.
    1   one or more behavior-risk or identity findings (things to confirm /
        scrub before release); or, with --strict, any finding.
    2   usage error (path missing, not a directory, bad flag).
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
LICENSE_NAMES = {
    "license", "license.md", "license.txt", "licence", "copying",
    "license-mit", "license-apache",
}
GITIGNORE_NAMES = {".gitignore"}

# Structural entrypoint files (presence is a signal of a runnable entrypoint).
ENTRYPOINT_FILES = {
    "makefile", "run.sh", "run.py", "main.py", "reproduce.sh", "reproduce.py",
    "repro.sh", "justfile", "dvc.yaml", "snakefile", "experiment.py",
}

# Directories we never descend into for *source* scanning ...
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    ".mypy_cache", ".pytest_cache", ".tox", ".idea", ".vscode", ".eggs",
}
# ... but these ones are themselves findings (junk that should not ship).
JUNK_DIRS = {"__pycache__", ".ipynb_checkpoints"}

# Source extensions to scan for in-code signals.
SOURCE_EXTS = {".py", ".sh", ".r", ".jl", ".lua", ".ipynb", ".m"}

# "Backup / superseded" file name smells -> dead-code candidates.
BACKUP_RE = re.compile(
    r"(\.bak$|\.old$|\.orig$|~$|"
    r"_v\d+(\.[A-Za-z0-9]+)?$|"
    r"[._-](old|bak|backup|copy|final|temp|tmp|draft|deprecated|unused|"
    r"experimental|test\d*)(\.[A-Za-z0-9]+)?$)",
    re.IGNORECASE,
)
# Pure junk files that should never be in a release.
JUNK_FILE_RE = re.compile(
    r"(\.pyc$|\.pyo$|\.DS_Store$|\.swp$|\.swo$|Thumbs\.db$|\.~lock|"
    r"\.coverage$|\.log$)",
    re.IGNORECASE,
)
# Large data/model blob extensions (flagged if big AND in-tree).
BLOB_EXTS = {
    ".pt", ".pth", ".ckpt", ".h5", ".hdf5", ".pkl", ".pickle", ".npz", ".npy",
    ".bin", ".onnx", ".safetensors", ".pb", ".tar", ".zip", ".gz", ".7z",
    ".parquet", ".feather", ".csv", ".tsv", ".json", ".jsonl", ".sqlite",
    ".db", ".mat",
}

# In-code seeding signals (case-insensitive). One hit means "seeding present".
SEED_RE = re.compile(
    r"(\brandom\.seed\s*\(|\bnp\.random\.seed\s*\(|\bnumpy\.random\.seed\s*\(|"
    r"\bnp\.random\.default_rng\s*\(|\btorch\.manual_seed\s*\(|"
    r"\btorch\.cuda\.manual_seed(?:_all)?\s*\(|\bset_seed\s*\(|"
    r"\bseed_everything\s*\(|\bpl\.seed_everything\s*\(|\bPYTHONHASHSEED\b|"
    r"\btf\.random\.set_seed\s*\(|\btf\.keras\.utils\.set_random_seed\s*\(|"
    r"\bset\.seed\s*\(|\bRandom\.seed!\s*\(|"
    r"\buse_deterministic_algorithms\s*\(|\bdeterministic\s*=\s*True)",
    re.IGNORECASE,
)
# Nondeterminism smells: RNG use, time-based seeds, threading/workers.
NONDET_PATTERNS = [
    (r"\bnp\.random\.(?:rand|randn|randint|choice|shuffle|permutation)\s*\(",
     "numpy RNG call"),
    (r"\brandom\.(?:random|randint|choice|shuffle|sample|uniform)\s*\(",
     "stdlib random call"),
    (r"\btorch\.(?:rand|randn|randint|randperm)\s*\(", "torch RNG call"),
    (r"\b(?:time\.time|datetime\.now|time\.time_ns)\s*\(\s*\)",
     "wall-clock value (often a time-based seed -> nondeterministic)"),
    (r"\bnum_workers\s*=\s*[^0]", "DataLoader num_workers>0 (loader order)"),
    (r"\bos\.environ\b", "reads environment (run-to-run config drift)"),
    (r"\bset\s*\(", "set() iteration order used as data?"),
]
NONDET_RES = [(re.compile(p, re.IGNORECASE), why) for p, why in NONDET_PATTERNS]

# Commented-out code block: a run of >=3 consecutive comment lines that LOOK
# like code (contain code-ish tokens), not prose.
CODEISH_RE = re.compile(
    r"[=()\[\]{}]|->|:=|\bdef\b|\bclass\b|\bimport\b|\bfor\b|\bwhile\b|"
    r"\bif\b|\breturn\b|\bprint\b|\.\w+\("
)
IF_FALSE_RE = re.compile(r"^\s*if\s+(False|0)\s*:", re.IGNORECASE)

# Magic-number / hardcoded-config smells (assignment of a bare numeric literal
# to a config-ish name, or an absolute path string).
HARDCODE_PATTERNS = [
    (r"\b(lr|learning_rate|batch_size|epochs|n_epochs|num_epochs|hidden|"
     r"hidden_dim|hidden_size|n_layers|num_layers|dropout|weight_decay|"
     r"momentum|temperature|seed|n_samples|num_samples|max_len|max_length|"
     r"warmup|patience|threshold|alpha|beta|gamma|k|top_k|n_clusters)"
     r"\s*=\s*-?\d+(?:\.\d+)?(?:e-?\d+)?\b",
     "hardcoded hyperparameter (move to config/CLI; preserve the value)"),
]
HARDCODE_RES = [(re.compile(p, re.IGNORECASE), why) for p, why in HARDCODE_PATTERNS]
# Absolute / home paths embedded in source.
ABSPATH_RE = re.compile(
    r"""['"](/(?:home|Users|mnt|data|scratch|content|workspace|tmp)/[^'"\n]+|"""
    r"""[A-Za-z]:\\[^'"\n]+|~/[^'"\n]+)['"]""")

# Identity (double-blind) surface leaks.
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
HOMEPATH_RE = re.compile(r"(/home/|/Users/)([A-Za-z0-9._-]+)")
GIT_URL_RE = re.compile(r"github\.com[/:]([\w.-]+)/", re.IGNORECASE)


def fail(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# A finding: (category, risk, path_or_loc, message)
Finding = tuple


class Audit:
    def __init__(self) -> None:
        self.findings: list[tuple[str, str, str, str]] = []
        self.has_readme = False
        self.readme_text = ""
        self.has_license = False
        self.has_gitignore = False
        self.has_entrypoint: list[str] = []
        self.has_main_guard = False
        self.has_console_scripts = False
        self.has_src_layout = False
        self.has_config_file = False
        self.seed_present = False
        self.top_level_scripts = 0
        self.n_source_files = 0
        self.scanned_files = 0
        self.truncated = False
        self.has_git_dir = False

    def add(self, cat: str, risk: str, loc: str, msg: str) -> None:
        self.findings.append((cat, risk, loc, msg))


CONFIG_FILE_NAMES = {
    "config.yaml", "config.yml", "config.json", "config.toml", "config.ini",
    "params.yaml", "params.yml", "hparams.yaml", "hydra", "configs", "conf",
}


def walk(root: Path, max_files: int, max_bytes: int, blind: str,
         names: list[str]) -> Audit:
    a = Audit()
    name_res = [re.compile(re.escape(n), re.IGNORECASE) for n in names if n]

    for path in sorted(root.rglob("*")):
        parts = path.parts
        # Detect (but do not descend into) a real .git dir -> history leak.
        if ".git" in parts:
            a.has_git_dir = True
        if any(p in SKIP_DIRS for p in parts):
            continue

        rel = path.relative_to(root).as_posix()

        if path.is_dir():
            nm = path.name.lower()
            if nm in JUNK_DIRS:
                a.add("hygiene", "safe", rel,
                      f"{path.name}/ should not ship -- gitignore + remove "
                      "from the release copy")
            if nm in {"src", "source"} or _looks_like_pkg(path):
                a.has_src_layout = True
            if nm in CONFIG_FILE_NAMES:
                a.has_config_file = True
            continue

        if not path.is_file():
            continue

        nm = path.name
        low = nm.lower()
        depth = rel.count("/")

        # ---- layout / docs files ----
        if low in README_NAMES and not a.has_readme:
            a.has_readme = True
            try:
                a.readme_text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                a.readme_text = ""
        if low in LICENSE_NAMES:
            a.has_license = True
        if low in GITIGNORE_NAMES:
            a.has_gitignore = True
        if low in CONFIG_FILE_NAMES:
            a.has_config_file = True
        if low in ENTRYPOINT_FILES:
            a.has_entrypoint.append(rel)

        # ---- hygiene / junk ----
        if JUNK_FILE_RE.search(nm):
            a.add("hygiene", "safe", rel,
                  "junk/build artifact -- exclude from the release copy")
        if BACKUP_RE.search(nm):
            a.add("dead-code", "behavior-risk", rel,
                  "looks like a backup/superseded file -- confirm nothing "
                  "imports or runs it, then remove (it may shadow the live "
                  "version and change which code runs)")

        # ---- large in-tree blobs ----
        ext = path.suffix.lower()
        if ext in BLOB_EXTS:
            try:
                sz = path.stat().st_size
            except OSError:
                sz = 0
            if sz >= max_bytes:
                a.add("hygiene", "behavior-risk", rel,
                      f"{_human(sz)} data/model blob committed in-tree -- "
                      "release via an archival host (Zenodo/Software Heritage) "
                      "or a download script, not in the repo; confirm it is not "
                      "needed at runtime before removing")

        # ---- identity surface (only when blind review) ----
        if blind in ("single", "double"):
            _scan_identity_name(a, rel, nm, name_res)

        # ---- count top-level scripts (flat-dump smell) ----
        if depth == 0 and ext in SOURCE_EXTS and low not in ENTRYPOINT_FILES:
            a.top_level_scripts += 1

        # ---- source content scan ----
        if ext in SOURCE_EXTS:
            a.n_source_files += 1
            if a.scanned_files >= max_files:
                a.truncated = True
                continue
            a.scanned_files += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            _scan_source(a, rel, text, blind, name_res)

    _finalize(a, root, blind)
    return a


def _looks_like_pkg(d: Path) -> bool:
    try:
        return (d / "__init__.py").is_file()
    except OSError:
        return False


def _scan_identity_name(a: Audit, rel: str, nm: str,
                        name_res: list[re.Pattern]) -> None:
    for nre in name_res:
        if nre.search(nm):
            a.add("identity", "identity", rel,
                  "filename contains an identifying term -- rename for "
                  "double-blind review")
            return


def _scan_source(a: Audit, rel: str, text: str, blind: str,
                 name_res: list[re.Pattern]) -> None:
    lines = text.splitlines()
    # seeding present anywhere?
    if SEED_RE.search(text):
        a.seed_present = True
    if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", text):
        a.has_main_guard = True
    if re.search(r"console_scripts|\[project\.scripts\]|entry_points", text):
        a.has_console_scripts = True

    comment_run_start = -1
    comment_run_codeish = 0
    is_py = rel.endswith(".py") or rel.endswith(".ipynb")

    for i, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        stripped = line.strip()

        # if False: / if 0: dead branch
        if IF_FALSE_RE.match(line):
            a.add("dead-code", "behavior-risk", f"{rel}:{i}",
                  "`if False:` / `if 0:` dead branch -- remove only after "
                  "confirming it is truly unreachable in every config")

        # commented-out code-looking lines (python-style # comments)
        if is_py and stripped.startswith("#") and CODEISH_RE.search(stripped):
            if comment_run_start < 0:
                comment_run_start = i
            comment_run_codeish += 1
        else:
            if comment_run_start >= 0 and comment_run_codeish >= 3:
                a.add("dead-code", "behavior-risk",
                      f"{rel}:{comment_run_start}-{i - 1}",
                      f"{comment_run_codeish} consecutive commented-out "
                      "code-like lines -- delete dead code (use version "
                      "control for history), but confirm it isn't a toggled "
                      "experiment path first")
            comment_run_start = -1
            comment_run_codeish = 0

        # hardcoded hyperparameters
        for hre, why in HARDCODE_RES:
            if hre.search(line) and not stripped.startswith("#"):
                a.add("config", "behavior-risk", f"{rel}:{i}", why)
                break

        # absolute / home paths
        m = ABSPATH_RE.search(line)
        if m and not stripped.startswith("#"):
            a.add("config", "behavior-risk", f"{rel}:{i}",
                  "absolute/home path hardcoded in source -- move to a config "
                  "or CLI arg so it runs on another machine (preserve the value)")

        # nondeterminism smells
        for nre, why in NONDET_RES:
            if nre.search(line) and not stripped.startswith("#"):
                a.add("determinism", "behavior-risk", f"{rel}:{i}",
                      f"{why} -- ensure it is seeded/ordered deterministically; "
                      "changing this changes results, so confirm with the author")
                break

        # identity content (blind review): emails, home paths, author names
        if blind in ("single", "double") and not _is_url_comment(stripped):
            em = EMAIL_RE.search(line)
            if em:
                a.add("identity", "identity", f"{rel}:{i}",
                      "email address in source -- scrub for double-blind")
            hp = HOMEPATH_RE.search(line)
            if hp:
                a.add("identity", "identity", f"{rel}:{i}",
                      f"home path reveals a username ('{hp.group(2)}') -- scrub")
            for nre in name_res:
                if nre.search(line):
                    a.add("identity", "identity", f"{rel}:{i}",
                          "identifying name/affiliation in source -- scrub for "
                          "double-blind")
                    break

    # flush a trailing comment run
    if comment_run_start >= 0 and comment_run_codeish >= 3:
        a.add("dead-code", "behavior-risk",
              f"{rel}:{comment_run_start}-{len(lines)}",
              f"{comment_run_codeish} consecutive commented-out code-like "
              "lines -- delete dead code, confirming it isn't a toggled path")


def _is_url_comment(s: str) -> bool:
    return s.startswith("#") and ("http://" in s or "https://" in s)


def _finalize(a: Audit, root: Path, blind: str) -> None:
    # README
    if not a.has_readme:
        a.add("layout", "safe", "(repo root)",
              "no README -- add one naming the entrypoint, the exact command "
              "to reproduce each result, deps, and the repo layout")
    elif a.readme_text and not re.search(
            r"(reproduce|to\s+run|usage|getting\s+started|```)",
            a.readme_text, re.IGNORECASE):
        a.add("entrypoint", "safe", "README",
              "README has no run/reproduce/usage section -- document the one "
              "command that runs the pipeline end to end")

    # LICENSE
    if not a.has_license:
        a.add("layout", "safe", "(repo root)",
              "no LICENSE -- add one (releasing without a license leaves reuse "
              "rights undefined; many artifact tracks expect it)")

    # .gitignore
    if not a.has_gitignore:
        a.add("layout", "safe", "(repo root)",
              "no .gitignore -- add one so caches/outputs/large blobs don't get "
              "released")

    # entrypoint
    ep = list(a.has_entrypoint)
    if a.has_main_guard:
        ep.append("__main__ guard")
    if a.has_console_scripts:
        ep.append("console_scripts")
    if not ep:
        a.add("entrypoint", "behavior-risk", "(repo root)",
              "no obvious entrypoint (Makefile / run.sh / __main__ / "
              "console_scripts) -- wire one documented command; doing this "
              "touches how the pipeline is invoked, so verify it runs the same")

    # layout: flat dump
    if a.top_level_scripts >= 8 and not a.has_src_layout:
        a.add("layout", "safe", "(repo root)",
              f"{a.top_level_scripts} source files dumped at the repo root and "
              "no src/ or package dir -- group into a package/src layout "
              "(moving files is mechanical; fix imports and re-run to confirm)")

    # config separation
    if not a.has_config_file and any(
            f[0] == "config" for f in a.findings):
        a.add("config", "safe", "(repo root)",
              "hyperparameters/paths are embedded in source and there is no "
              "config file -- add one (config.yaml / argparse) and move the "
              "values into it UNCHANGED")

    # determinism: no seeding at all
    if not a.seed_present:
        a.add("determinism", "behavior-risk", "(repo root)",
              "no seed-setting found anywhere -- runs are nondeterministic; set "
              "and RECORD seeds (random/numpy/framework + PYTHONHASHSEED). "
              "Adding seeds changes the numbers, so coordinate with the author "
              "and re-confirm the paper's results")

    # git history leak (blind)
    if blind in ("single", "double") and a.has_git_dir:
        a.add("identity", "identity", ".git/",
              ".git history present -- commit author/email identify you; ship "
              "an anonymized export without .git, or use anonymous.4open.science")


def _human(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{n}B"


RISK_ORDER = {"identity": 0, "behavior-risk": 1, "safe": 2}


def report_text(root: Path, a: Audit) -> str:
    lines = [f"release_audit: {root}"]
    note = (f"  scanned {a.scanned_files}/{a.n_source_files} source files "
            "for in-code signals")
    if a.truncated:
        note += " (truncated; raise --max-files)"
    lines.append(note)
    lines.append("")

    findings = sorted(
        a.findings,
        key=lambda f: (RISK_ORDER.get(f[1], 9), f[0], f[2]))
    if not findings:
        lines.append("  no release-refactor findings.")
        return "\n".join(lines)

    for cat, risk, loc, msg in findings:
        tag = {"identity": "IDENTITY", "behavior-risk": "ASK-FIRST",
               "safe": "SAFE"}.get(risk, risk.upper())
        lines.append(f"  [{tag:>9}] ({cat}) {loc}")
        lines.append(f"            {msg}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("path", help="path to the research-code directory to audit")
    p.add_argument("--blind", choices=["none", "single", "double"],
                   default="none",
                   help="review blind level; enables identity/leak scanning "
                        "(default: none)")
    p.add_argument("--names", default="",
                   help="comma-separated identifying terms to scan for "
                        "(author names, institutions, project codenames)")
    p.add_argument("--json", action="store_true",
                   help="emit a machine-readable JSON report")
    p.add_argument("--strict", action="store_true",
                   help="exit 1 on ANY finding (not just behavior-risk/identity)")
    p.add_argument("--max-files", type=int, default=2000, metavar="N",
                   help="max source files to scan for in-code signals "
                        "(default 2000)")
    p.add_argument("--max-bytes", type=int, default=10 * 1024 * 1024,
                   metavar="N",
                   help="in-tree blob size (bytes) above which a data/model "
                        "file is flagged (default 10MB)")
    args = p.parse_args()

    root = Path(args.path)
    if not root.exists():
        fail(f"path not found: {args.path}")
    if not root.is_dir():
        fail(f"not a directory: {args.path} (point at the code dir, not a file)")
    if args.max_files < 1:
        fail("--max-files must be >= 1")
    if args.max_bytes < 1:
        fail("--max-bytes must be >= 1")

    names = [n.strip() for n in args.names.split(",") if n.strip()]
    a = walk(root, args.max_files, args.max_bytes, args.blind, names)

    risk = [f for f in a.findings if f[1] == "behavior-risk"]
    ident = [f for f in a.findings if f[1] == "identity"]
    safe = [f for f in a.findings if f[1] == "safe"]

    if args.json:
        payload = {
            "path": str(root),
            "blind": args.blind,
            "findings": [
                {"category": c, "risk": r, "location": loc, "message": m}
                for c, r, loc, m in sorted(
                    a.findings,
                    key=lambda f: (RISK_ORDER.get(f[1], 9), f[0], f[2]))
            ],
            "summary": {
                "identity": len(ident),
                "behavior_risk": len(risk),
                "safe": len(safe),
                "total": len(a.findings),
            },
            "seed_present": a.seed_present,
            "has_readme": a.has_readme,
            "has_license": a.has_license,
            "scanned_files": a.scanned_files,
            "source_files": a.n_source_files,
            "truncated": a.truncated,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(report_text(root, a))
        print()
        print(f"RESULT: {len(ident)} identity, {len(risk)} ask-first "
              f"(behavior-risk), {len(safe)} safe finding(s).")
        if ident:
            print("  -> scrub IDENTITY findings before any blind-review upload "
                  "(hand the deep sweep to anonymize-paper).")
        if risk:
            print("  -> ASK-FIRST findings could change the paper's numbers if "
                  "done carelessly. Confirm with the author and re-verify "
                  "results before/after each edit. NEVER auto-apply.")
        print("NOTE: this is a static map of opportunities, not proof the repo "
              "reproduces. Behavior-preservation is verified by re-running the "
              "pipeline (test-research-code / verify-results), not by this scan.")

    if ident or risk or (args.strict and a.findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
