#!/usr/bin/env python3
"""Lint a reproducibility-artifact directory for submission/badging readiness.

Part of the prepare-artifacts skill (research-paper-skills). Stdlib only, no
network. Scans an artifact FOLDER (a code/data repo prepared for an artifact
evaluation or an "Artifacts Available" deposit) and reports, with file paths,
how close it is to the community-standard bars:

  completeness   the ML Code Completeness Checklist (paperswithcode, used by
                 NeurIPS) — exactly 5 items: (1) dependency spec
                 (requirements.txt / environment.yml / setup.py / pyproject /
                 Dockerfile), (2) training code, (3) evaluation code,
                 (4) pre-trained models or a documented way to obtain them,
                 (5) a README with a RESULTS TABLE and the EXACT command to
                 reproduce each result.
  archival       whether the README/artifact points only at a GitHub/personal
                 URL (NOT acceptable for USENIX-family "Artifacts Available",
                 which require Zenodo/FigShare/Dryad/Software Heritage with a
                 version-specific DOI/SWHID) — flags GitHub-only hosting and
                 looks for a DOI / SWHID / archival link.
  anonymization  for a DOUBLE-BLIND review-phase artifact: author names/emails,
                 institutional paths, non-anonymized GitHub/personal URLs, and
                 git history that would de-anonymize (.git present) — pass
                 --blind double (or let --venue supply it).
  hygiene        a LICENSE file (artifact-evaluation expects a clear license),
                 an artifact appendix / README, oversized files vs a ZIP cap.

What this script CANNOT verify (stays manual / live): that the build actually
runs, that results reproduce within tolerance, the venue's CURRENT badge
offering (fetch the live Call for Artifacts), and that a DOI actually resolves.

Usage:
    python3 check_artifact.py <artifact_dir> [--venue venues/conferences/<v>.yml]
                              [--blind double|single|none] [--zip-cap-mb 100]
                              [--json] [--strict]

Exit codes: 0 no errors | 1 errors (or warnings with --strict) | 2 usage.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

try:
    from venue_profile import ProfileError, load_profile
except Exception:  # pragma: no cover - venue support is optional
    ProfileError = Exception  # type: ignore

    def load_profile(*_a, **_k):  # type: ignore
        raise ProfileError("venue_profile module not available")


# Directories never worth scanning for content / never counted toward size.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", ".venv", "venv", "env", ".idea", ".vscode", ".ipynb_checkpoints",
}

DEP_FILES = (
    "requirements.txt", "environment.yml", "environment.yaml", "setup.py",
    "setup.cfg", "pyproject.toml", "Pipfile", "poetry.lock", "Dockerfile",
    "renv.lock", "DESCRIPTION", "conda.yaml", "spack.yaml",
)
LICENSE_NAMES = ("LICENSE", "LICENCE", "COPYING", "LICENSE.md", "LICENSE.txt")
README_NAMES = ("README.md", "README.rst", "README.txt", "README",
                "ARTIFACT.md", "ARTIFACT-APPENDIX.md", "INSTALL.md")

TRAIN_HINT = re.compile(r"(?:^|[/_\-])(train|training|pretrain|finetune|fit)\b", re.I)
EVAL_HINT = re.compile(r"(?:^|[/_\-])(eval|evaluate|evaluation|test|inference|predict|benchmark|score)\b", re.I)
MODEL_EXT = (".pt", ".pth", ".ckpt", ".h5", ".pb", ".onnx", ".safetensors",
             ".bin", ".pkl", ".joblib", ".model", ".npz", ".weights")
CODE_EXT = (".py", ".ipynb", ".sh", ".R", ".jl", ".cpp", ".cc", ".c", ".java",
            ".go", ".rs", ".m", ".lua", ".scala")

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
ZENODO_RE = re.compile(r"zenodo\.org|figshare\.com|datadryad\.org|dryad", re.I)
SWHID_RE = re.compile(r"swh:1:(?:cnt|dir|rev|rel|snp):[0-9a-f]{40}", re.I)
SWH_URL_RE = re.compile(r"softwareheritage\.org|archive\.softwareheritage", re.I)
GITHUB_RE = re.compile(r"https?://(?:www\.)?(?:github|gitlab|bitbucket)\.com/[\w.\-]+/[\w.\-]+", re.I)
ANON_REPO_RE = re.compile(r"anonymous\.4open\.science|anonymous\.github|4open\.science", re.I)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# crude "looks like a person's full name" (Title-cased two tokens) — used only
# inside author/contact contexts, never as a blanket scan.
AUTHORISH_RE = re.compile(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b")
RESULTS_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$", re.M)  # markdown table row
COMMAND_HINT_RE = re.compile(
    r"(?:^|\n)\s*(?:\$|>>>|#)?\s*(?:python3?|bash|sh|make|docker|conda|pip|"
    r"sbatch|Rscript|julia|./run|./reproduce)\b", re.I)


class Report:
    def __init__(self) -> None:
        self.findings: list[dict] = []

    def add(self, severity: str, check: str, where: str, message: str) -> None:
        self.findings.append(
            {"severity": severity, "check": check, "where": where, "message": message}
        )

    def count(self, sev: str) -> int:
        return sum(1 for f in self.findings if f["severity"] == sev)


def walk(root: pathlib.Path):
    """Yield (relative_path, absolute_path) for every file, skipping junk dirs."""
    for p in sorted(root.rglob("*")):
        parts = set(p.relative_to(root).parts)
        if parts & SKIP_DIRS:
            continue
        if p.is_file():
            yield p.relative_to(root), p


def read_text(p: pathlib.Path, limit: int = 400_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def find_readme(files):
    # prefer top-level README/ARTIFACT files, shallowest first
    cands = [(rel, ab) for rel, ab in files if rel.name in README_NAMES]
    cands.sort(key=lambda t: (len(t[0].parts), t[0].name.lower()))
    return cands[0] if cands else None


# ---------------------------------------------------------------------------
# Completeness — the 5-item ML Code Completeness Checklist
# ---------------------------------------------------------------------------

def check_completeness(root, files, rep: Report) -> dict:
    names = [rel for rel, _ in files]
    flat = {rel.name for rel in names}
    status = {}

    # (1) dependency specification
    deps = [rel for rel in names if rel.name in DEP_FILES]
    status["dependencies"] = bool(deps)
    if deps:
        rep.add("INFO", "complete/dependencies",
                ", ".join(str(d) for d in deps[:4]),
                "dependency specification present")
    else:
        rep.add("ERROR", "complete/dependencies", str(root),
                "no dependency spec found (requirements.txt / environment.yml / "
                "setup.py / pyproject.toml / Dockerfile) — item 1 of the ML Code "
                "Completeness Checklist")

    code = [rel for rel in names if rel.suffix in CODE_EXT]
    # (2) training code
    train = [rel for rel in code if TRAIN_HINT.search(str(rel))]
    status["training_code"] = bool(train)
    if train:
        rep.add("INFO", "complete/training-code", str(train[0]),
                f"training code present ({len(train)} file(s) match train/fit)")
    else:
        rep.add("WARN", "complete/training-code", str(root),
                "no file looks like training code (train/training/finetune/fit) "
                "— item 2; if the method is not trained, say so in the README")

    # (3) evaluation code
    ev = [rel for rel in code if EVAL_HINT.search(str(rel))]
    status["evaluation_code"] = bool(ev)
    if ev:
        rep.add("INFO", "complete/evaluation-code", str(ev[0]),
                f"evaluation code present ({len(ev)} file(s) match eval/test)")
    else:
        rep.add("WARN", "complete/evaluation-code", str(root),
                "no file looks like evaluation code (eval/evaluate/test/"
                "benchmark/inference) — item 3")

    # (4) pre-trained models (or a documented way to fetch them)
    models = [rel for rel, _ in files if rel.suffix.lower() in MODEL_EXT]
    status["pretrained_models"] = bool(models)
    if models:
        rep.add("INFO", "complete/pretrained-models", str(models[0]),
                f"{len(models)} model/checkpoint file(s) present")
    else:
        rep.add("INFO", "complete/pretrained-models", str(root),
                "no checkpoint files found — item 4 is satisfied either by "
                "shipping pre-trained models OR documenting how to obtain them "
                "(large weights belong on Zenodo, not in the repo); verify in "
                "the README")

    # (5) README with a results table + exact reproduction command
    readme = find_readme(files)
    has_table = has_cmd = False
    if readme:
        rel, ab = readme
        text = read_text(ab)
        has_table = len(RESULTS_TABLE_RE.findall(text)) >= 2  # header + >=1 row
        has_cmd = bool(COMMAND_HINT_RE.search(text))
        if has_table and has_cmd:
            rep.add("INFO", "complete/readme", str(rel),
                    "README has a results table and a runnable command")
        else:
            missing = []
            if not has_table:
                missing.append("a results table")
            if not has_cmd:
                missing.append("the exact reproduce command")
            rep.add("WARN", "complete/readme", str(rel),
                    "README present but missing " + " and ".join(missing) +
                    " — item 5 wants a table of results AND the precise command "
                    "to reproduce each")
    else:
        rep.add("ERROR", "complete/readme", str(root),
                "no README/ARTIFACT file found — item 5 of the checklist and a "
                "hard requirement for any artifact evaluation")
    # README item (5) counts as satisfied only with BOTH a table and a command.
    status["readme"] = bool(readme) and has_table and has_cmd
    status["readme_results_table"] = has_table
    status["readme_reproduce_cmd"] = has_cmd

    core = ("dependencies", "training_code", "evaluation_code",
            "pretrained_models", "readme")
    n = sum(1 for k in core if status.get(k))
    rep.add("INFO", "complete/score", str(root),
            f"ML Code Completeness: {n}/5 items satisfied "
            "(dependencies, training, evaluation, models, README table+command)")
    return status


# ---------------------------------------------------------------------------
# Archival hosting readiness
# ---------------------------------------------------------------------------

def check_archival(root, files, readme, rep: Report) -> None:
    corpus_parts = []
    if readme:
        corpus_parts.append(read_text(readme[1]))
    # also scan small metadata files that often carry the DOI
    for rel, ab in files:
        if rel.name.lower() in ("citation.cff", "codemeta.json", ".zenodo.json",
                                "readme.md", "artifact.md", "artifact-appendix.md"):
            corpus_parts.append(read_text(ab))
    corpus = "\n".join(corpus_parts)

    has_doi = bool(DOI_RE.search(corpus)) or bool(ZENODO_RE.search(corpus))
    has_swhid = bool(SWHID_RE.search(corpus)) or bool(SWH_URL_RE.search(corpus))
    has_github = bool(GITHUB_RE.search(corpus))

    if has_doi or has_swhid:
        kinds = []
        if has_doi:
            kinds.append("DOI/Zenodo-class")
        if has_swhid:
            kinds.append("Software Heritage SWHID")
        rep.add("INFO", "archival/identifier", str(root),
                "archival identifier referenced (" + ", ".join(kinds) + "); for "
                "the FINAL deposit use a VERSION-specific DOI, not a concept DOI")
    elif has_github:
        rep.add("WARN", "archival/github-only", str(root),
                "the artifact references a GitHub/GitLab/Bitbucket URL but no "
                "archival DOI/SWHID — USENIX-family 'Artifacts Available' "
                "explicitly REJECT GitHub/personal sites for the permanent copy; "
                "deposit to Zenodo/FigShare/Dryad (version DOI) and/or Software "
                "Heritage and cite that identifier")
    else:
        rep.add("WARN", "archival/no-identifier", str(root),
                "no archival identifier (DOI/SWHID) found in the README/metadata "
                "— required for an 'Artifacts Available' badge; add a Zenodo "
                "version DOI or a Software Heritage SWHID")

    # CITATION.cff / codemeta help the archive emit BibTeX — nudge, not error.
    have_meta = any(rel.name.lower() in ("citation.cff", "codemeta.json")
                    for rel, _ in files)
    if not have_meta:
        rep.add("INFO", "archival/metadata", str(root),
                "no CITATION.cff / codemeta.json — adding one makes Zenodo / "
                "Software Heritage emit correct citation metadata")


# ---------------------------------------------------------------------------
# Anonymization (double-blind review-phase artifact)
# ---------------------------------------------------------------------------

def check_anonymization(root, files, blind, rep: Report) -> None:
    if blind not in ("double", "triple"):
        rep.add("INFO", "anon/skipped", str(root),
                f"blind level {blind!r}: anonymization scan skipped (pass "
                "--blind double to force it for a double-blind submission)")
        return

    if (root / ".git").exists():
        rep.add("ERROR", "anon/git-history", str(root / ".git"),
                "a .git directory is present — git history/authors/remote will "
                "de-anonymize the artifact; ship an anonymized ZIP or use "
                "anonymous.4open.science instead of the raw repo")

    contact_ctx = re.compile(r"(?i)\b(author|authors|maintainer|contact|"
                             r"copyright|written by|created by|by\s+[A-Z])\b")
    n_email = n_github = n_name = 0
    for rel, ab in files:
        if rel.suffix.lower() not in (".md", ".rst", ".txt", ".py", ".cff",
                                      ".json", ".toml", ".cfg", "") and \
                rel.name not in README_NAMES and rel.name not in LICENSE_NAMES:
            continue
        text = read_text(ab, limit=120_000)
        for m in EMAIL_RE.finditer(text):
            if "example.com" in m.group(0) or "anonymous" in m.group(0).lower():
                continue
            n_email += 1
            if n_email <= 5:
                rep.add("ERROR", "anon/email", str(rel),
                        f"author/contact email present: {m.group(0)!r}")
        for m in GITHUB_RE.finditer(text):
            if ANON_REPO_RE.search(m.group(0)):
                continue
            n_github += 1
            if n_github <= 5:
                rep.add("ERROR", "anon/identifying-url", str(rel),
                        f"non-anonymized repo/personal URL: {m.group(0)!r} — "
                        "swap for an anonymized mirror")
        # names only inside an author/contact context, to avoid false positives
        for line in text.splitlines():
            if contact_ctx.search(line):
                nm = AUTHORISH_RE.search(line)
                if nm and "Example" not in nm.group(0):
                    n_name += 1
                    if n_name <= 5:
                        rep.add("WARN", "anon/possible-name", str(rel),
                                f"possible author name in a contact/author line: "
                                f"{nm.group(0)!r} — confirm and remove for "
                                "double-blind")
                    break
    if n_email == 0 and n_github == 0 and n_name == 0 and not (root / ".git").exists():
        rep.add("INFO", "anon/clean", str(root),
                "no obvious identity leaks found in scanned text files — still "
                "check PDF/appendix metadata and large data files manually")


# ---------------------------------------------------------------------------
# Hygiene
# ---------------------------------------------------------------------------

def check_hygiene(root, files, zip_cap_mb, rep: Report) -> None:
    if not any(rel.name in LICENSE_NAMES for rel, _ in files):
        rep.add("WARN", "hygiene/license", str(root),
                "no LICENSE/COPYING file — artifact evaluation expects a clear "
                "license; pick one (e.g. MIT/BSD/Apache-2.0 for code, "
                "CC-BY/CC0 for data) so reviewers may legally run/reuse it")

    total = 0
    big = []
    for rel, ab in files:
        try:
            sz = ab.stat().st_size
        except OSError:
            continue
        total += sz
        if sz > 50 * 1024 * 1024:
            big.append((rel, sz))
    total_mb = total / (1024 * 1024)
    if zip_cap_mb and total_mb > zip_cap_mb:
        rep.add("WARN", "hygiene/size", str(root),
                f"artifact is ~{total_mb:.0f} MB, over the {zip_cap_mb} MB cap "
                "common for review-system uploads (e.g. NeurIPS ZIP) — host "
                "large data/models on Zenodo and link with an anonymous URL")
    for rel, sz in big[:5]:
        rep.add("INFO", "hygiene/large-file", str(rel),
                f"large file (~{sz / (1024 * 1024):.0f} MB) — consider an "
                "external archival deposit instead of bundling it")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lint a reproducibility-artifact directory for badging / "
        "submission readiness: ML Code Completeness (5 items), archival-hosting "
        "(DOI/SWHID vs GitHub-only), double-blind anonymization, and hygiene "
        "(license, size). Stdlib only, no network. Advisory — it never proves "
        "the build runs or the results reproduce.",
        epilog="examples:\n"
        "  python3 check_artifact.py ./artifact\n"
        "  python3 check_artifact.py ./artifact --blind double --json\n"
        "  python3 check_artifact.py ./artifact --venue venues/conferences/neurips-2026.yml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("artifact_dir", help="path to the artifact directory/repo")
    ap.add_argument("--venue", help="venues/conferences/<v>.yml (supplies the "
                    "blind level if --blind is omitted)")
    ap.add_argument("--venues-dir", help="venues/ root (auto-discovered)")
    ap.add_argument("--blind", choices=["double", "triple", "single", "none"],
                    help="review blind level (overrides the venue profile)")
    ap.add_argument("--zip-cap-mb", type=int, default=100,
                    help="upload size cap to warn above (default 100; NeurIPS "
                    "review ZIP); set 0 to disable")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on warnings too")
    args = ap.parse_args()

    root = pathlib.Path(args.artifact_dir)
    if not root.is_dir():
        print(f"error: artifact directory not found: {root}", file=sys.stderr)
        return 2

    notes: list[str] = []
    blind = args.blind
    if blind is None and args.venue:
        try:
            profile, pnotes = load_profile(args.venue, args.venues_dir)
            notes.extend(pnotes)
            blind = str((profile.get("review") or {}).get("blind") or "").lower() or None
            if blind:
                notes.append(f"blind level from venue profile: {blind}")
        except ProfileError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if blind is None:
        blind = "none"
        notes.append("no --blind and no venue profile; anonymization scan "
                     "skipped (pass --blind double for a double-blind artifact)")

    files = list(walk(root))
    if not files:
        print(f"error: no files found under {root} (after skipping VCS/cache "
              "dirs)", file=sys.stderr)
        return 2

    rep = Report()
    status = check_completeness(root, files, rep)
    readme = find_readme(files)
    check_archival(root, files, readme, rep)
    check_anonymization(root, files, blind, rep)
    check_hygiene(root, files, args.zip_cap_mb, rep)

    errors, warns = rep.count("ERROR"), rep.count("WARN")
    verdict = ("FAIL" if errors else
               "PASS-WITH-WARNINGS" if warns else "PASS")

    if args.json:
        json.dump({"verdict": verdict, "errors": errors, "warnings": warns,
                   "completeness": status, "blind": blind,
                   "findings": rep.findings, "notes": notes},
                  sys.stdout, indent=2, default=str)
        print()
    else:
        order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        for f in sorted(rep.findings, key=lambda f: order[f["severity"]]):
            print(f"{f['severity']:5s} {f['check']:28s} {str(f['where'])[:40]:>40s}  "
                  f"{f['message']}")
        for n in notes:
            print(f"note: {n}")
        print(f"\nverdict: {verdict} (errors={errors}, warnings={warns}, blind={blind})")
        print("reminder: this lint covers the FILES only — it cannot prove the "
              "build runs, that results reproduce within tolerance, or that a "
              "DOI resolves. Re-verify the venue's CURRENT artifact rules live.")
    if errors or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
