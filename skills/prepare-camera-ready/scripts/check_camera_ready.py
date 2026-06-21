#!/usr/bin/env python3
"""Lint a camera-ready LaTeX source for leftover submission-mode artifacts.

Part of the prepare-camera-ready skill (research-paper-skills). Stdlib only,
no network. Checks the FINAL (post-acceptance) .tex against the venue's
camera-ready rail:

  every rail   leftover review/anonymous options, "Anonymous Author"
               placeholders, anonymized repo links, missing author block,
               line numbers / todo notes, missing acknowledgments at
               formerly-blind venues, page-count risk from a sibling .log
  acm-taps     rights/DOI block (\\setcopyright \\acmConference \\acmISBN
               \\acmDOI), placeholder DOI/ISBN values, CCS concepts, keywords
  ieee-        IEEEtran class, page-number suppression, copyright-notice
  pdfexpress   reminder, plus the manual PDF eXpress / eCF steps it CANNOT see
  openreview-  current-year style file with the [final] option (no
  direct       preprint/submission mode)

What this script can NEVER verify: rights-form completion, PDF eXpress
certification, eCF title match, registration. Those stay manual.

Usage:
    python3 check_camera_ready.py final.tex --venue venues/conferences/<v>.yml [--track T]

Exit codes: 0 no errors | 1 errors (or warnings with --strict) | 2 usage.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

from venue_profile import (
    ProfileError,
    expected_style_package,
    load_profile,
    pick_track,
)

MAX_DEPTH = 6

# ---------------------------------------------------------------------------
# Source gathering: read the main .tex, follow \input/\include, strip comments
# ---------------------------------------------------------------------------

_INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")
_COMMENT_RE = re.compile(r"(?<!\\)%.*$")


def strip_comment(line: str) -> str:
    return _COMMENT_RE.sub("", line)


def gather(path: pathlib.Path, root: pathlib.Path, seen: set, depth: int,
           notes: list[str]) -> list[tuple[str, int, str]]:
    """Return [(display_path, lineno, comment-stripped line), ...]."""
    rp = path.resolve()
    if rp in seen or depth > MAX_DEPTH:
        return []
    seen.add(rp)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        notes.append(f"could not read {path}: {exc}")
        return []
    rows: list[tuple[str, int, str]] = []
    disp = str(path)
    for i, raw in enumerate(text.splitlines(), 1):
        line = strip_comment(raw)
        rows.append((disp, i, line))
        for m in _INPUT_RE.finditer(line):
            target = m.group(1).strip()
            sub = root / target
            if not sub.suffix:
                sub = sub.with_suffix(".tex")
            if sub.is_file():
                rows.extend(gather(sub, root, seen, depth + 1, notes))
            else:
                notes.append(f"{disp}:{i}: \\input target not found: {target}")
    return rows


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.findings: list[dict] = []

    def add(self, severity: str, check: str, where: str, message: str) -> None:
        self.findings.append(
            {"severity": severity, "check": check, "where": where, "message": message}
        )

    def count(self, sev: str) -> int:
        return sum(1 for f in self.findings if f["severity"] == sev)


def find_first(rows, pattern):
    rx = re.compile(pattern)
    for path, no, line in rows:
        m = rx.search(line)
        if m:
            return path, no, m
    return None


def find_all(rows, pattern):
    rx = re.compile(pattern)
    out = []
    for path, no, line in rows:
        for m in rx.finditer(line):
            out.append((path, no, m))
    return out


_DOCCLASS_RE = re.compile(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}")


def doc_class(rows):
    hit = find_first(rows, _DOCCLASS_RE.pattern)
    if not hit:
        return None
    path, no, m = hit
    opts = [o.strip() for o in (m.group(1) or "").split(",") if o.strip()]
    return path, no, m.group(2).strip(), opts


# ---------------------------------------------------------------------------
# Generic checks (all rails)
# ---------------------------------------------------------------------------

def check_generic(rows, profile, rail, rep: Report) -> None:
    dc = doc_class(rows)
    if dc:
        path, no, cls, opts = dc
        for bad in ("review", "anonymous", "submission"):
            if any(o == bad or o.startswith(bad + "=") for o in opts):
                rep.add("ERROR", "final/submission-mode-option", f"{path}:{no}",
                        f"documentclass still carries [{bad}] — camera-ready "
                        "must drop submission/review-mode options")
    else:
        rep.add("WARN", "final/no-documentclass", "-",
                "no \\documentclass found — is this the main .tex file?")

    for path, no, m in find_all(
        rows,
        r"(?i)anonymous\s+(?:author|institution|affiliation|submission)|"
        r"\\author\s*\{\s*Anonymous|under\s+(?:double-)?blind\s+review",
    ):
        rep.add("ERROR", "final/anonymous-placeholder", f"{path}:{no}",
                f"anonymization placeholder still present: {m.group(0)!r}")

    for path, no, m in find_all(
        rows, r"anonymous\.4open\.science|anonymous\.github|anonymized[-_.]?(?:repo|link|url)"
    ):
        rep.add("ERROR", "final/anonymized-link", f"{path}:{no}",
                f"anonymized artifact link still present: {m.group(0)!r} — "
                "swap in the real repository URL")

    if not find_first(rows, r"\\author\b"):
        rep.add("ERROR", "final/missing-author-block", "-",
                "no \\author command found — restore the real author block "
                "(names, affiliations, emails)")

    for path, no, m in find_all(
        rows, r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{(lineno|todonotes)\}|\\linenumbers\b|\\todo\s*\{|\\listoftodos\b"
    ):
        rep.add("WARN", "final/review-artifact", f"{path}:{no}",
                f"review-time artifact still present: {m.group(0)!r}")

    for path, no, m in find_all(rows, r"pdfauthor\s*=\s*\{\s*(Anonymous[^}]*|)\}"):
        rep.add("WARN", "final/pdf-metadata", f"{path}:{no}",
                "hyperref pdfauthor is empty/Anonymous — set the real authors "
                "in the PDF metadata")

    blind = str((profile.get("review") or {}).get("blind") or "").lower()
    if blind in ("double", "triple"):
        if not find_first(
            rows,
            r"\\begin\{acks\}|\\section\*?\{[^}]*[Aa]cknowledg|\\acknowledgments\b|\\acks\b",
        ):
            rep.add("WARN", "final/acknowledgments-missing", "-",
                    f"venue was {blind}-blind and no acknowledgments section "
                    "found — restore acknowledgments and funding/grant numbers")


# ---------------------------------------------------------------------------
# Rail-specific checks
# ---------------------------------------------------------------------------

_PLACEHOLDER_VAL = re.compile(r"n{4,}|x{4,}|1122445|10\.1145/1122|YY/MM", re.IGNORECASE)


def check_acm(rows, rep: Report) -> None:
    required = {
        "\\setcopyright": r"\\setcopyright\s*\{",
        "\\acmDOI": r"\\acmDOI\s*\{",
        "\\acmISBN": r"\\acmISBN\s*\{",
    }
    for name, pat in required.items():
        if not find_first(rows, pat):
            rep.add("ERROR", "acm/rights-block-missing", "-",
                    f"{name} not found — paste the rights/DOI block returned "
                    "by the completed ACM eRights form into the preamble")
    if not find_first(rows, r"\\acmConference\s*[\[{]") and not find_first(
            rows, r"\\acmJournal\s*\{"):
        rep.add("ERROR", "acm/rights-block-missing", "-",
                "\\acmConference (or \\acmJournal) not found — part of the "
                "eRights rights/DOI block")
    if not find_first(rows, r"\\acmYear\s*\{"):
        rep.add("WARN", "acm/rights-block-missing", "-",
                "\\acmYear not found — usually included in the eRights block")

    for cmd in ("acmDOI", "acmISBN"):
        for path, no, m in find_all(rows, r"\\%s\s*\{([^}]*)\}" % cmd):
            val = m.group(1).strip()
            if not val or _PLACEHOLDER_VAL.search(val):
                rep.add("ERROR", "acm/placeholder-rights-value", f"{path}:{no}",
                        f"\\{cmd}{{{val}}} looks like the acmart template "
                        "placeholder — replace it with the value from YOUR "
                        "eRights confirmation")

    if not find_first(rows, r"\\begin\{CCSXML\}") or not find_first(rows, r"\\ccsdesc"):
        rep.add("ERROR", "acm/ccs-concepts-missing", "-",
                "CCS concepts missing (CCSXML block + \\ccsdesc) — generate "
                "them at https://dl.acm.org/ccs; TAPS requires them")
    if not find_first(rows, r"\\keywords\s*\{"):
        rep.add("ERROR", "acm/keywords-missing", "-",
                "\\keywords{...} missing — mandatory in ACM camera-ready")

    dc = doc_class(rows)
    if dc and dc[2] != "acmart":
        rep.add("WARN", "acm/unexpected-class", f"{dc[0]}:{dc[1]}",
                f"documentclass is {dc[2]!r}, expected acmart for the TAPS rail")


def check_ieee(rows, rep: Report) -> None:
    dc = doc_class(rows)
    if dc and dc[2] != "IEEEtran":
        rep.add("WARN", "ieee/unexpected-class", f"{dc[0]}:{dc[1]}",
                f"documentclass is {dc[2]!r}, expected IEEEtran")
    for path, no, m in find_all(
        rows, r"\\pagenumbering\s*\{|\\pagestyle\s*\{(?!empty)|\\thispagestyle\s*\{(?!empty)|\\setcounter\s*\{page\}"
    ):
        rep.add("WARN", "ieee/page-numbers", f"{path}:{no}",
                f"{m.group(0)!r} — IEEE Xplore camera-ready PDFs must not "
                "carry page numbers/headers/footers (proceedings add them)")
    if not find_first(rows, r"\\IEEEpubid|\\IEEEoverridecommandlockouts"):
        rep.add("INFO", "ieee/copyright-notice", "-",
                "no \\IEEEpubid found — many IEEE conferences require the "
                "page-1 copyright notice; the exact ISBN/price string is in "
                "the venue's camera-ready instructions")
    rep.add("INFO", "ieee/manual-steps", "-",
            "not checkable from source: PDF eXpress validation (conference "
            "ID), certified-file naming, eCF exact-title match, registration "
            "— see references/ieee-pdfexpress-rail.md")


_STYLE_RE = re.compile(
    r"\\usepackage\s*(?:\[([^\]]*)\])?\s*\{((?:neurips_\d{4})|(?:icml\d{4})|(?:iclr\d{4}_conference)|(?:aaai\d{2,4}))\}"
)


def check_neurips(rows, profile, rep: Report) -> None:
    expected = expected_style_package(profile)
    hits = find_all(rows, _STYLE_RE.pattern)
    if not hits:
        rep.add("ERROR", "neurips/style-file-missing", "-",
                "no venue style package (\\usepackage{neurips_YYYY} / "
                "icmlYYYY / iclrYYYY_conference) found")
        return
    for path, no, m in hits:
        opts = [o.strip() for o in (m.group(1) or "").split(",") if o.strip()]
        pkg = m.group(2)
        if expected and pkg != expected:
            rep.add("ERROR", "neurips/style-file-year", f"{path}:{no}",
                    f"style file is {pkg!r} but this venue/year requires "
                    f"{expected!r} — recompile with the current year's style")
        bad = [o for o in opts if o in ("preprint", "submission")]
        if bad:
            rep.add("ERROR", "neurips/not-final-mode", f"{path}:{no}",
                    f"style option [{bad[0]}] is not camera-ready mode — "
                    "switch to [final]")
        elif "final" not in opts:
            rep.add("ERROR", "neurips/not-final-mode", f"{path}:{no}",
                    f"\\usepackage{{{pkg}}} lacks the [final] option — "
                    "without it the camera-ready stays anonymized")


# ---------------------------------------------------------------------------
# Page-count risk (best effort, from a sibling .log)
# ---------------------------------------------------------------------------

_LOG_PAGES_RE = re.compile(r"Output written on .*?\((\d+) pages?")
_EXTRA_RE = re.compile(r"\+\s*(\d+)")


def check_pages(tex: pathlib.Path, profile, track, rep: Report) -> None:
    log = tex.with_suffix(".log")
    if not log.is_file() or not track or not track.get("page_limit"):
        return
    m = None
    try:
        for m in _LOG_PAGES_RE.finditer(log.read_text(errors="replace")):
            pass
    except OSError:
        return
    if not m:
        return
    pages = int(m.group(1))
    limit = int(track["page_limit"])
    extra_str = str((profile.get("camera_ready") or {}).get("extra_pages") or "")
    em = _EXTRA_RE.search(extra_str)
    allowed = limit + (int(em.group(1)) if em else 0)
    if pages > allowed:
        rep.add("WARN", "final/page-limit-risk", str(log),
                f"compiled PDF has {pages} pages vs track limit {limit}"
                + (f" (+{em.group(1)} camera-ready allowance)" if em else "")
                + " — verify what the limit excludes (refs/appendix) and the "
                "venue's camera-ready allowance before assuming you fit")
    else:
        rep.add("INFO", "final/page-count", str(log),
                f"compiled PDF has {pages} pages (track limit {limit}"
                + (f", camera-ready allowance {allowed}" if allowed != limit else "")
                + ")")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

RAIL_CHECKS = {
    "acm-taps": "acm",
    "ieee-pdfexpress": "ieee",
    "openreview-direct": "neurips",
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lint a camera-ready .tex for leftover submission-mode "
        "artifacts and missing rail-specific blocks (ACM rights/DOI block, "
        "IEEE page-number rules, NeurIPS [final] mode).",
        epilog="examples:\n"
        "  python3 check_camera_ready.py final.tex --venue venues/conferences/sigspatial-2026.yml --track Research\n"
        "  python3 check_camera_ready.py final.tex --venue venues/conferences/neurips-2026.yml --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("tex", help="main camera-ready .tex file")
    ap.add_argument("--venue", required=True,
                    help="path to venues/conferences/<venue>.yml")
    ap.add_argument("--track", help="track name substring (for page limits)")
    ap.add_argument("--venues-dir", help="venues/ root (auto-discovered)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on warnings too")
    ap.add_argument("--no-inputs", action="store_true",
                    help="do not follow \\input/\\include")
    args = ap.parse_args()

    tex = pathlib.Path(args.tex)
    if not tex.is_file():
        print(f"error: tex file not found: {tex}", file=sys.stderr)
        return 2
    try:
        profile, notes = load_profile(args.venue, args.venues_dir)
        track, note = pick_track(profile, args.track)
        notes.append(note)
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rows_notes: list[str] = []
    if args.no_inputs:
        text = tex.read_text(encoding="utf-8", errors="replace")
        rows = [(str(tex), i, strip_comment(line))
                for i, line in enumerate(text.splitlines(), 1)]
    else:
        rows = gather(tex, tex.parent, set(), 0, rows_notes)
    notes.extend(rows_notes)

    cam = profile.get("camera_ready") or {}
    rail = cam.get("rail") or {
        "acmart": "acm-taps",
        "IEEEtran": "ieee-pdfexpress",
        "neurips": "openreview-direct",
    }.get(str((profile.get("format") or {}).get("template") or ""), "unknown")

    rep = Report()
    check_generic(rows, profile, rail, rep)
    kind = RAIL_CHECKS.get(rail)
    if kind == "acm":
        check_acm(rows, rep)
    elif kind == "ieee":
        check_ieee(rows, rep)
    elif kind == "neurips":
        check_neurips(rows, profile, rep)
    else:
        rep.add("INFO", "final/unknown-rail", "-",
                f"camera-ready rail {rail!r} has no rail-specific lints; "
                "generic checks only — follow the venue's own instructions")
    check_pages(tex, profile, track, rep)

    errors, warns = rep.count("ERROR"), rep.count("WARN")
    verdict = ("FAIL" if errors else
               "PASS-WITH-WARNINGS" if warns else "PASS")
    if args.json:
        json.dump({"rail": rail, "verdict": verdict, "errors": errors,
                   "warnings": warns, "findings": rep.findings,
                   "notes": notes}, sys.stdout, indent=2, default=str)
        print()
    else:
        order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        for f in sorted(rep.findings, key=lambda f: order[f["severity"]]):
            print(f"{f['severity']:5s} {f['check']:32s} {f['where']:>24s}  {f['message']}")
        for n in notes:
            print(f"note: {n}")
        print(f"\nverdict: {verdict} (rail={rail}, errors={errors}, warnings={warns})")
        print("reminder: a clean lint covers the SOURCE only — rights forms, "
              "PDF eXpress, eCF, and registration remain manual steps.")
    if errors or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
