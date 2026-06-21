#!/usr/bin/env python3
"""Build the abstract-registration artifact for a venue.

Most ML/data venues (NeurIPS, ICML, KDD, CVPR, CHI, SIGSPATIAL, ...) require
registering title + abstract + authors + topics + conflicts 2-7 days BEFORE
the full-paper deadline. This script assembles everything the user must
enter into the submission form as one reviewable Markdown card, with the
deadline math done from the venue profile.

It PREPARES the card only — it never submits anything anywhere.

Usage:
    python3 abstract_registration.py --venue venues/conferences/<id>.yml \\
        --title "Paper title" [--abstract-file abstract.txt|main.tex] \\
        [--authors "Name <email> (Affiliation)"]... [--topics "t1; t2"] \\
        [--coi-file conflicts.txt] [--track Research] \\
        [--today YYYY-MM-DD] [--out card.md]

Exit codes: 0 ok, 2 bad arguments / unreadable input.
"""

import argparse
import datetime
import os
import sys

import venueyaml
from abstract_check import (_ABSTRACT_RE, _PLACEHOLDER_RE, latex_words,
                            resolve_inputs, strip_comments)


def _parse_date(value):
    try:
        return datetime.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _fmt_deadline(value, today, tz):
    d = _parse_date(value)
    if d is None:
        return "%s (%s) — could not parse for countdown" % (value, tz)
    delta = (d - today).days
    if delta < 0:
        status = "PASSED %d days ago" % -delta
    elif delta == 0:
        status = "TODAY"
    else:
        status = "in %d days" % delta
    return "%s (%s) — %s" % (d.isoformat(), tz, status)


COI_TEMPLATE = """\
Fill this in by walking your last ~5 years of papers and your lab roster
(each venue's form states its own window and categories — follow the form):

- [ ] Co-authors within the venue's window (commonly the last 3-5 years)
- [ ] Current and former advisors / advisees (usually a permanent conflict)
- [ ] Everyone at your current institution(s) (some venues: past 12 months too)
- [ ] Funding, financial, or close personal relationships
- [ ] Anyone who has seen this draft or discussed it in depth
"""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Assemble an abstract-registration card (title, abstract, "
        "authors, topics, COI, deadline math) from a venue profile. "
        "Prepares only; never submits.")
    parser.add_argument("--venue", required=True, help="venue profile .yml")
    parser.add_argument("--title", required=True, help="working paper title")
    parser.add_argument("--abstract-file", default=None,
                        help="abstract text file, or a .tex (abstract env is "
                        "extracted); omit to leave a TODO slot")
    parser.add_argument("--authors", action="append", default=[],
                        help="repeatable: 'Name <email> (Affiliation)'")
    parser.add_argument("--topics", default=None,
                        help="semicolon-separated topics/subject areas")
    parser.add_argument("--coi-file", default=None,
                        help="text file, one conflict entry per line")
    parser.add_argument("--track", default=None,
                        help="track name — quotes that track's profile notes")
    parser.add_argument("--today", default=None,
                        help="override today's date (YYYY-MM-DD), for testing")
    parser.add_argument("--out", default=None,
                        help="write the card here instead of stdout")
    args = parser.parse_args(argv)

    if not args.title.strip():
        sys.stderr.write("error: --title must not be empty\n")
        return 2

    today = _parse_date(args.today) if args.today else datetime.date.today()
    if today is None:
        sys.stderr.write("error: --today must be YYYY-MM-DD\n")
        return 2

    try:
        profile = venueyaml.load_with_family(args.venue)
    except venueyaml.VenueYamlError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2

    # --- abstract ---
    abstract, abs_words = None, 0
    if args.abstract_file:
        if not os.path.isfile(args.abstract_file):
            sys.stderr.write("error: file not found: %s\n" % args.abstract_file)
            return 2
        with open(args.abstract_file, "r", encoding="utf-8",
                  errors="replace") as fh:
            raw = fh.read()
        if args.abstract_file.endswith(".tex"):
            body = resolve_inputs(strip_comments(raw),
                                  os.path.dirname(os.path.abspath(args.abstract_file)))
            m = _ABSTRACT_RE.search(body)
            if not m:
                sys.stderr.write("error: no \\begin{abstract} found in %s\n"
                                 % args.abstract_file)
                return 2
            abstract = m.group(1).strip()
        else:
            abstract = raw.strip()
        if not abstract:
            sys.stderr.write("error: abstract in %s is empty\n"
                             % args.abstract_file)
            return 2
        abs_words = len(latex_words(abstract))

    # --- COI ---
    coi_entries = []
    if args.coi_file:
        if not os.path.isfile(args.coi_file):
            sys.stderr.write("error: file not found: %s\n" % args.coi_file)
            return 2
        with open(args.coi_file, "r", encoding="utf-8", errors="replace") as fh:
            coi_entries = [l.strip() for l in fh if l.strip()]

    # --- profile facts ---
    vname = profile.get("name") or profile.get("id") or args.venue
    cfp = profile.get("cfp_url", "n/a")
    deadlines = profile.get("deadlines") or {}
    tz = deadlines.get("timezone") or "timezone unstated — assume nothing"
    d_abs, d_paper = deadlines.get("abstract"), deadlines.get("paper")
    review = profile.get("review") or {}
    fmt = profile.get("format") or {}
    limits = fmt.get("abstract_words")
    ver = profile.get("verified") or {}

    track_note = None
    if args.track:
        for t in profile.get("tracks") or []:
            if isinstance(t, dict) and str(t.get("name", "")).lower() == args.track.lower():
                track_note = t.get("notes")
                break
        if track_note is None:
            sys.stderr.write("warning: track %r not found in the profile — "
                             "card uses venue-level deadlines only\n" % args.track)

    # --- build card ---
    L = []
    L.append("# Abstract registration — %s" % vname)
    L.append("")
    L.append("> Preparation artifact only. Enter these values into the "
             "submission form yourself; this skill never submits on your "
             "behalf.")
    L.append("")
    L.append("## Deadlines (verify on the live CFP before relying: %s)" % cfp)
    L.append("")
    da, dp = _parse_date(d_abs), _parse_date(d_paper)
    if d_abs:
        L.append("- Abstract registration: %s" % _fmt_deadline(d_abs, today, tz))
        L.append("- Full paper: %s" % _fmt_deadline(d_paper, today, tz)
                 if d_paper else "- Full paper: not in profile — check the CFP")
        if da and dp:
            L.append("- Gap between abstract and paper deadline: %d days"
                     % (dp - da).days)
        L.append("- Placeholder warning: several venues delete placeholder "
                 "titles/abstracts or desk-reject submissions whose final "
                 "abstract diverges greatly from the registered one — "
                 "register real text.")
    else:
        L.append("- No separate abstract-registration deadline in the profile; "
                 "the abstract is due with the paper%s. Use this card as the "
                 "submission-form prep sheet."
                 % (" on %s" % _fmt_deadline(d_paper, today, tz) if d_paper else ""))
    if track_note:
        L.append("- Track notes (%s, from profile): %s"
                 % (args.track, " ".join(str(track_note).split())))
    L.append("")
    L.append("## Title")
    L.append("")
    L.append(args.title.strip())
    L.append("")
    L.append("(%d words, %d characters)"
             % (len(args.title.split()), len(args.title.strip())))
    L.append("")
    L.append("## Abstract")
    L.append("")
    if abstract:
        L.append(abstract)
        L.append("")
        ph = _PLACEHOLDER_RE.search(abstract)
        if ph:
            warn = ("placeholder text %r found in this abstract — do NOT "
                    "register it as-is; several venues (e.g. KDD, AAAI) delete "
                    "or desk-reject placeholder abstracts" % ph.group(0))
            L.append("**WARNING: %s.**" % warn)
            L.append("")
            sys.stderr.write("warning: %s\n" % warn)
        if isinstance(limits, list) and len(limits) == 2:
            ok = limits[0] <= abs_words <= limits[1]
            L.append("(%d words — venue limit %d-%d: %s)"
                     % (abs_words, limits[0], limits[1],
                        "OK" if ok else "OUT OF RANGE"))
        else:
            L.append("(%d words — no venue-mandated limit in the profile; "
                     "150-250 is the common convention)" % abs_words)
    else:
        L.append("TODO — draft it with the write-abstract skill, then rerun "
                 "with --abstract-file. Do not register placeholder text.")
    L.append("")
    L.append("## Authors (order matters; many venues freeze the list at a "
             "deadline — check the CFP)")
    L.append("")
    if args.authors:
        for a in args.authors:
            L.append("- %s" % a)
    else:
        L.append("- TODO — list every author as 'Name <email> (Affiliation)', "
                 "final order")
    L.append("")
    L.append("## Topics / subject areas")
    L.append("")
    if args.topics:
        for t in [t.strip() for t in args.topics.split(";") if t.strip()]:
            L.append("- %s" % t)
        L.append("")
        L.append("Match these against the official list in the submission "
                 "form — forms only accept their own taxonomy.")
    else:
        L.append("- TODO — pick from the submission form's own topic list "
                 "(forms only accept their own taxonomy)")
    L.append("")
    L.append("## Conflicts of interest")
    L.append("")
    if coi_entries:
        for c in coi_entries:
            L.append("- %s" % c)
        L.append("")
        L.append("Cross-check against the venue's stated COI window and "
                 "categories in the form.")
    else:
        L.append(COI_TEMPLATE.rstrip())
    L.append("")
    L.append("## Where to register")
    L.append("")
    L.append("- System: %s" % (review.get("submission_system") or "not in profile"))
    L.append("- URL: %s" % (review.get("submission_url") or "not in profile"))
    L.append("")
    L.append("## Verification record")
    L.append("")
    L.append("- Profile: %s (verified %s, confidence: %s)"
             % (profile.get("id", args.venue), ver.get("date", "unknown"),
                ver.get("confidence", "unknown")))
    L.append("- Re-verify every deadline and the timezone on the live CFP "
             "before relying on this card: %s" % cfp)
    L.append("- Card generated: %s" % today.isoformat())
    L.append("")

    card = "\n".join(L)
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(card)
        except OSError as exc:
            sys.stderr.write("error: cannot write %s: %s\n" % (args.out, exc))
            return 2
        print("wrote %s" % args.out)
    else:
        sys.stdout.write(card)
    return 0


if __name__ == "__main__":
    sys.exit(main())
