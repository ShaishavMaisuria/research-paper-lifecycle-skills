#!/usr/bin/env python3
"""Emit the correct LaTeX keywords block for a venue family.

Styles (pick one via --style, or derive it from a venue profile via --venue):

  ccs    ACM CCS Concepts skeleton (CCSXML + \\ccsdesc placeholders that MUST
         be filled from the official tool at https://dl.acm.org/ccs — this
         script never invents concept ids) plus a filled \\keywords{} line.
  ieee   \\begin{IEEEkeywords} ... \\end{IEEEkeywords} (Index Terms).
  lncs   \\keywords{First \\and Second \\and Third} (3-6 keywords expected).
  none   No in-paper block (NeurIPS-style families); prints guidance only.

Usage:
    python3 keywords_block.py --style lncs --keywords "spatial indexing, query processing, road networks"
    python3 keywords_block.py --venue venues/conferences/sigspatial-2026.yml --keywords "..."
    python3 keywords_block.py --style ieee --keywords "..." --sort

Exit codes: 0 ok, 2 bad arguments / unreadable profile.
"""

import argparse
import sys

import venueyaml

_PROFILE_TO_STYLE = {
    "ccs-concepts": "ccs",
    "ieee-index-terms": "ieee",
    "lncs-keywords": "lncs",
    "none": "none",
}

CCS_SKELETON = """\
%% --- ACM CCS Concepts (REQUIRED at ACM venues) ------------------------------
%% Do NOT hand-write or guess concept ids. Generate this block officially:
%%   1. Open https://dl.acm.org/ccs and search for 1-4 fitting concepts.
%%   2. Assign significance per concept: 500 = primary, 300 = secondary,
%%      100 = minor.
%%   3. Click "Generate CCS Codes" and paste BOTH outputs below, replacing
%%      the placeholder lines.
\\begin{CCSXML}
<!-- PASTE the generated XML from https://dl.acm.org/ccs here -->
\\end{CCSXML}
%% PASTE the generated \\ccsdesc lines here, e.g.:
%% \\ccsdesc[500]{REPLACE-WITH-GENERATED-CONCEPT}

\\keywords{%(kw_comma)s}
"""

IEEE_BLOCK = """\
%% Place directly after the abstract. IEEE convention: alphabetical order,
%% terms drawn from the IEEE Thesaurus where possible.
\\begin{IEEEkeywords}
%(kw_comma)s
\\end{IEEEkeywords}
"""

LNCS_BLOCK = """\
%% Place directly after the abstract (llncs renders middle-dot separators).
\\keywords{%(kw_and)s}
"""

NONE_NOTE = """\
This venue family has no in-paper keywords/CCS block (NeurIPS-style):
topic/subject areas are selected in the submission form (e.g. OpenReview)
at abstract-registration time, not typeset in the paper. Do not add a
\\keywords or CCSXML block; pick subject areas in the form instead.
"""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print the LaTeX keywords block for a venue family. "
        "Never fabricates ACM CCS concept ids — routes to dl.acm.org/ccs.")
    parser.add_argument("--style", choices=["ccs", "ieee", "lncs", "none"],
                        help="block style (or use --venue to derive it)")
    parser.add_argument("--venue", help="venue profile .yml; derives the style "
                        "from format.keywords")
    parser.add_argument("--keywords", default="",
                        help="comma-separated author keywords")
    parser.add_argument("--sort", action="store_true",
                        help="sort keywords alphabetically (IEEE convention)")
    args = parser.parse_args(argv)

    style = args.style
    if args.venue:
        try:
            profile = venueyaml.load_with_family(args.venue)
        except venueyaml.VenueYamlError as exc:
            sys.stderr.write("error: %s\n" % exc)
            return 2
        pk = ((profile.get("format") or {}).get("keywords"))
        derived = _PROFILE_TO_STYLE.get(pk)
        if derived is None:
            sys.stderr.write("error: profile %s has no recognized "
                             "format.keywords value (%r); pass --style and "
                             "verify the live CFP\n" % (args.venue, pk))
            return 2
        if style and style != derived:
            sys.stderr.write("error: --style %s contradicts the profile's %s "
                             "(%s); drop one\n" % (style, pk, args.venue))
            return 2
        style = derived
    if not style:
        sys.stderr.write("error: pass --style or --venue\n")
        return 2

    kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if args.sort:
        kws = sorted(kws, key=str.lower)

    if style == "none":
        sys.stdout.write(NONE_NOTE)
        return 0
    if not kws:
        sys.stderr.write("error: --keywords is required for style %s "
                         "(comma-separated)\n" % style)
        return 2

    if style == "lncs" and not 3 <= len(kws) <= 6:
        sys.stderr.write("warning: %d keyword(s) — Springer guidance and most "
                         "LNCS CFPs ask for 3-6\n" % len(kws))
    if style == "ieee" and kws != sorted(kws, key=str.lower):
        sys.stderr.write("warning: Index Terms are conventionally alphabetical "
                         "— rerun with --sort to apply\n")

    if style == "ccs":
        sys.stdout.write(CCS_SKELETON % {"kw_comma": ", ".join(kws)})
    elif style == "ieee":
        sys.stdout.write(IEEE_BLOCK % {"kw_comma": ", ".join(kws)})
    elif style == "lncs":
        sys.stdout.write(LNCS_BLOCK % {"kw_and": " \\and ".join(kws)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
