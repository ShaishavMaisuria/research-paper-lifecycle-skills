#!/usr/bin/env python3
"""Scaffold a new venue-profile YAML under venues/conferences/.

Part of the add-venue-profile skill (research-paper-skills). Stdlib only;
offline; deterministic. Emits a schema-shaped skeleton with every field
present, nulls + TODO comments where facts must come from the live CFP,
and a pre-filled `verified:` provenance block at `needs-verification`.

The skeleton intentionally fails `validate_profile.py --strict` until a
human (or agent) fills it from the live CFP — the validator's warnings
double as the contributor's TODO list.

Exit codes: 0 ok | 2 usage/config error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

SKELETON = """\
# =============================================================================
# Venue profile: {name}
# Scaffolded by add-venue-profile/scripts/init_profile.py on {today}.
# Fill every TODO from the LIVE CFP — never from memory. A wrong page limit
# or deadline can cause someone's desk reject. Schema: venues/schema.yml
# Validate before the PR:
#   python3 skills/add-venue-profile/scripts/validate_profile.py {relpath} --strict
# =============================================================================

# --- identity ----------------------------------------------------------------
id: {id}
name: {name}{name_todo}
family: {family}
year: {year}
cfp_url: {cfp_url}{cfp_todo}
website: null                 # TODO: conference homepage

# --- venue identity across APIs (the alias table) ----------------------------
aliases:
  dblp_key: null              # TODO: conf/<key> or journals/<key> — look up via
                              # https://dblp.org/search/venue/api?q=<venue>&format=json
  s2_venue: null              # TODO: Semantic Scholar venue string (often differs
                              # from DBLP, e.g. SIGSPATIAL is "SIGSPATIAL/GIS")
  crossref_container: null    # TODO: substring matching the Crossref proceedings
                              # container-title across years
  openalex_source: null       # often unavailable for ACM proceedings; null is honest

# --- deadlines (record the CFP's stated timezone; AoE is common, NOT universal)
deadlines:
  abstract: null              # TODO: abstract registration, if separate (it usually is)
  paper: null                 # TODO: YYYY-MM-DD
  rebuttal_start: null
  rebuttal_end: null
  notification: null
  camera_ready: null
  timezone: null              # TODO: AoE | PT | ET | UTC ... exactly as the CFP states

# --- tracks -------------------------------------------------------------------
tracks:
  - name: Research            # TODO: one entry per track verified against the CFP
    page_limit: null          # TODO: integer
    page_limit_excludes: []   # TODO: what does NOT count, e.g. [references, appendix];
                              # [] only when the limit explicitly includes everything
    notes: >
      TODO: quote the CFP's page-limit sentence VERBATIM here, plus
      track-specific deadlines if they differ from the main table.

# --- format -------------------------------------------------------------------
format:
  template: null              # TODO: acmart | IEEEtran | neurips | llncs | chi-manuscript
  documentclass: null         # TODO: exact invocation, e.g.
                              # "\\\\documentclass[sigconf,review,anonymous]{{acmart}}"
                              # (anonymous ONLY for double/triple-blind venues)
  columns: null
  abstract_words: null        # [min, max], or null if the CFP mandates nothing
  keywords: null              # ccs-concepts | ieee-index-terms | lncs-keywords | none
  required_sections: []       # e.g. [neurips-checklist, ai-use-acknowledgement]

# --- review process -----------------------------------------------------------
review:
  blind: null                 # TODO: single | double | triple — per the CFP's own words
  submission_system: null     # openreview | cmt | easychair | hotcrp | pcs | scholarone
  submission_url: null
  rebuttal_format: null       # none | openreview-thread | one-page-pdf | revise-and-resubmit
  rebuttal_limit: null        # e.g. "10000 chars per review" | "1 page PDF"
  llm_policy: null            # TODO: VERBATIM quote of the venue's AI/LLM-use policy.
                              # Never paraphrase — paraphrase can invert compliance.
  dual_submission: null       # TODO: VERBATIM quote of the dual-submission policy

# --- camera-ready rail ----------------------------------------------------------
camera_ready:
  rail: null                  # acm-taps | ieee-pdfexpress | springer |
                              # openreview-direct | scholarone-final-files
  extra_pages: null           # e.g. "+1 content page allowed at camera-ready"
  requirements: []            # ordered venue-specific checklist items

# --- provenance (mandatory — profiles without it are not merged) ----------------
verified:
  date: {today}
  source_urls:{source_urls}
  confidence: needs-verification   # upgrade to verified-live ONLY when every
                                   # critical fact came off live pages today
"""


def fail(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def find_repo_root(start: Path) -> Path | None:
    for cand in [start, *start.parents]:
        if (cand / "venues" / "schema.yml").is_file():
            return cand
    script = Path(__file__).resolve()
    if len(script.parents) >= 4:
        cand = script.parents[3]
        if (cand / "venues" / "schema.yml").is_file():
            return cand
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Scaffold a schema-shaped venue-profile YAML skeleton in "
                    "venues/conferences/. Offline and deterministic; every fact "
                    "still has to be filled from the LIVE CFP afterwards.",
        epilog="examples:\n"
               "  python3 init_profile.py mdm-2026 --family ieee-conf \\\n"
               "      --cfp-url https://mdm2026.example.org/cfp\n"
               "  python3 init_profile.py tist --family acm-journal --year 2026 --stdout\n"
               "exit codes: 0 ok | 2 usage/config error",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("venue_id",
                    help="kebab-case profile id; year-versioned for conferences "
                         "(e.g. mdm-2026), bare for rolling journals (e.g. tist)")
    ap.add_argument("--family", required=True,
                    help="venue family — must match a file in venues/families/ "
                         "(e.g. acm-sigconf, ieee-conf, neurips-style, lncs)")
    ap.add_argument("--cfp-url", default=None,
                    help="live CFP / author-instructions URL (strongly recommended)")
    ap.add_argument("--name", default=None,
                    help="full venue name (default: derived from the id)")
    ap.add_argument("--year", type=int, default=None,
                    help="venue year (default: parsed from a -YYYY id suffix)")
    ap.add_argument("--repo-root", type=Path, default=None,
                    help="repo root containing venues/ (default: auto-detected)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing file (NEVER use this to turn last "
                         "year's profile into this year's — copy forward instead)")
    ap.add_argument("--stdout", action="store_true",
                    help="print the skeleton instead of writing a file")
    args = ap.parse_args()

    vid = args.venue_id.strip()
    if not KEBAB.match(vid):
        fail(f"id {vid!r} is not kebab-case (lowercase letters, digits, hyphens)")

    year = args.year
    m = re.search(r"-(\d{4})$", vid)
    if m:
        suffix_year = int(m.group(1))
        if year is not None and year != suffix_year:
            fail(f"--year {year} contradicts the id's year suffix {suffix_year}")
        year = suffix_year
    if year is None:
        fail(f"id {vid!r} has no -YYYY suffix; pass --year explicitly "
             "(conference profiles should be year-versioned, e.g. mdm-2026)")
    if not 2000 <= year <= 2100:
        fail(f"year {year} looks implausible")

    root = args.repo_root or find_repo_root(Path.cwd())
    if args.repo_root and not (args.repo_root / "venues" / "schema.yml").is_file():
        fail(f"--repo-root {args.repo_root} has no venues/schema.yml")

    if root is not None:
        fam_dir = root / "venues" / "families"
        if not (fam_dir / f"{args.family}.yml").is_file():
            known = sorted(p.stem for p in fam_dir.glob("*.yml"))
            fail(f"family {args.family!r} has no venues/families/{args.family}.yml. "
                 f"Known families: {known}. Pick one of these, or add the family "
                 "file first (see venues/schema.yml).")
    else:
        print("[warn] could not locate the repo root, so the family was not "
              "checked against venues/families/", file=sys.stderr)

    cfp = (args.cfp_url or "").strip() or None
    if cfp is not None and not cfp.startswith(("http://", "https://")):
        fail(f"--cfp-url must be an absolute http(s) URL, got {cfp!r}")

    name = args.name or " ".join(
        w.upper() if len(w) <= 9 and not w.isdigit() else w.capitalize()
        for w in vid.split("-"))
    today = dt.date.today().isoformat()
    if cfp:
        source_urls = (f"\n    - {cfp}"
                       "\n      # TODO: add every page you extract facts from, and"
                       "\n      # annotate which facts each page supplied")
    else:
        source_urls = " []            # TODO: list every page you extract facts from"
    relpath = f"venues/conferences/{vid}.yml"

    text = SKELETON.format(
        id=vid, name=name,
        name_todo="" if args.name else
        "   # TODO: full official name, e.g. \"ACM SIGSPATIAL 2026 (34th ...)\"",
        family=args.family, year=year,
        cfp_url=cfp or "null",
        cfp_todo="" if cfp else "          # TODO: the live CFP / author-instructions page",
        today=today, source_urls=source_urls, relpath=relpath,
    )

    if args.stdout:
        sys.stdout.write(text)
        return 0
    if root is None:
        fail("not inside the research-paper-skills repo (no venues/schema.yml "
             "found). Run from the repo, pass --repo-root, or use --stdout.")
    out = root / "venues" / "conferences" / f"{vid}.yml"
    if out.exists() and not args.force:
        fail(f"{out} already exists. Profiles are year-versioned on purpose: "
             "create a NEW file for a new year instead of editing the old one "
             "(or pass --force only to redo a scaffold you just made).")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"scaffolded {out}")
    print("next: fetch the live CFP (scripts/fetch_cfp.py), fill every TODO, then run\n"
          f"  python3 skills/add-venue-profile/scripts/validate_profile.py {relpath} --strict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
