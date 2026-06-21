#!/usr/bin/env python3
"""Point-coverage and evidence-anchor checker for rebuttal drafts.

Stdlib only, fully offline. Verifies two deterministic properties:

1. COVERAGE — every reviewer point ID in the triage matrix appears in at
   least one response file. Point-ID convention (defined by this skill and
   `triage-reviews`): `R<reviewer>.<n>` for reviewer points (R1.1, R2.3),
   `AC.<n>` for area-chair / meta-review points, `MR.<n>` for a separate
   meta-review. IDs are matched case-sensitively as whole tokens.

2. ANCHORS — every '## ' response section contains at least one evidence
   anchor: a reference to a paper section, table, figure, equation,
   appendix, line number (L123 / "lines 120-124"), or citation bracket.
   Unanchored sections are reported as warnings (errors with --strict),
   because an unanchored rebuttal claim reads as assertion, not evidence.
   Text before the first '## ' heading (file-level notes, not a response
   box) is scanned for coverage but exempt from the anchor requirement.

Exit codes: 0 = all points covered (and anchored, if --strict),
            1 = missing points (or unanchored sections with --strict),
            2 = bad input / error.

Examples:
    python3 check_coverage.py points.md responses.md
    python3 check_coverage.py points.md r1.md r2.md r3.md --strict
"""

import argparse
import re
import sys

POINT_ID_RE = re.compile(r"\b((?:R\d+|AC|MR)\.\d+)\b")

ANCHOR_RE = re.compile(
    r"(?ix)"
    r"(\bsec(?:tion)?s?[.\s~]*\d)"          # Sec. 4 / Section 4.2
    r"|(\btable[s]?[.\s~]*\d)"              # Table 3
    r"|(\bfig(?:ure)?s?[.\s~]*\d)"          # Fig. 2 / Figure 2
    r"|(\beq(?:uation)?s?[.\s~]*\(?\d)"     # Eq. (5)
    r"|(\bappendix\s+[a-z0-9])"             # Appendix B
    r"|(\blines?\s+\d+)"                    # line 120 / lines 120-124
    r"|(\bL\d{2,}\b)"                       # L123
    r"|(\babstract\b)"                      # the abstract
    r"|(\[\d+(?:,\s*\d+)*\])"               # [12] / [3, 7]
)


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    return 2


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def split_sections(text):
    """[(title, body)] split on '## ' headings; preamble kept if non-empty."""
    sections = []
    title = "(preamble)"
    buf = []
    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("###"):
            sections.append((title, "\n".join(buf)))
            title = line[3:].strip() or "(untitled section)"
            buf = []
        else:
            buf.append(line)
    sections.append((title, "\n".join(buf)))
    return [(t, b.strip("\n")) for t, b in sections
            if not (t == "(preamble)" and not b.strip())]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check that a rebuttal draft addresses every triaged "
        "reviewer point (IDs like R1.2, AC.1) and that each response section "
        "anchors its claims to paper evidence (Sec./Table/Fig./line refs). "
        "Offline; stdlib only.")
    parser.add_argument("points",
                        help="triage matrix file containing the point IDs "
                        "(e.g. the output of the triage-reviews skill)")
    parser.add_argument("responses", nargs="+",
                        help="one or more response draft files (markdown/.tex)")
    parser.add_argument("--strict", action="store_true",
                        help="also fail (exit 1) on unanchored response sections")
    args = parser.parse_args(argv)

    try:
        points_text = read(args.points)
    except OSError as exc:
        return fail("cannot read points file %s: %s" % (args.points, exc))
    point_ids = []
    for pid in POINT_ID_RE.findall(points_text):
        if pid not in point_ids:
            point_ids.append(pid)
    if not point_ids:
        return fail("no point IDs (R<k>.<n> / AC.<n> / MR.<n>) found in %s — "
                    "is this a triage matrix?" % args.points)

    response_texts = {}
    for path in args.responses:
        try:
            response_texts[path] = read(path)
        except OSError as exc:
            return fail("cannot read response file %s: %s" % (path, exc))
    all_responses = "\n".join(response_texts.values())
    response_ids = set(POINT_ID_RE.findall(all_responses))

    covered = [p for p in point_ids if p in response_ids]
    missing = [p for p in point_ids if p not in response_ids]
    orphans = sorted(response_ids - set(point_ids))

    unanchored = []
    n_sections = 0
    for path, text in response_texts.items():
        for title, body in split_sections(text):
            n_sections += 1
            if title == "(preamble)":
                continue  # file-level notes, not a response box
            if not ANCHOR_RE.search(body):
                unanchored.append("%s :: %s" % (path, title))

    print("# Rebuttal coverage report")
    print("- points file: %s (%d point IDs)" % (args.points, len(point_ids)))
    print("- response files: %s (%d sections)"
          % (", ".join(response_texts), n_sections))
    print()
    print("## Coverage: %d/%d points addressed" % (len(covered), len(point_ids)))
    if missing:
        print()
        print("MISSING — these triaged points appear in NO response:")
        for p in missing:
            print("  - %s" % p)
    if orphans:
        print()
        print("Warning — IDs used in responses but absent from the matrix "
              "(typo or untriaged point?): %s" % ", ".join(orphans))
    print()
    if unanchored:
        print("## Anchors: %d section(s) contain NO evidence anchor "
              "(Sec./Table/Fig./Eq./Appendix/line/[n]):" % len(unanchored))
        for s in unanchored:
            print("  - %s" % s)
        print("An unanchored response reads as assertion — point each claim "
              "at the paper or concede the point.")
    else:
        print("## Anchors: every section contains at least one evidence anchor.")

    if missing:
        print()
        print("RESULT: FAIL — %d point(s) unaddressed." % len(missing))
        return 1
    if unanchored and args.strict:
        print()
        print("RESULT: FAIL (strict) — unanchored sections present.")
        return 1
    print()
    print("RESULT: PASS — all points addressed%s."
          % ("" if not unanchored else " (anchor warnings above)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
