#!/usr/bin/env python3
"""Rank survey candidate papers by a transparent composite score.

Stdlib only. Input: a JSON list of candidate papers (from find-papers), each a
dict that may contain: title, year, venue, citation_count, n_citers_in_set
(citation-graph centrality within the candidate pool), is_survey.
Output: the same papers sorted best-first with a printed reading list and a
`score` + `why` on each. No network; it ranks what it's given.

Composite (weights in references/ranking-criteria.md), each normalized to 0-1:
  impact   0.45  log-scaled citation count (seminal work surfaces)
  central  0.25  share of the candidate pool that cites it (in-area importance)
  recency  0.20  newer is up-weighted so SOTA isn't buried under old classics
  venue    0.10  a light tier bump for strong venues
A survey/review gets a small flag bonus so at least one lands near the top.
"""
import argparse
import datetime as dt
import json
import math
import sys

DEFAULT_STRONG_VENUE_HINTS = (
    "sigspatial", "gis", "tkde", "vldb", "sigmod", "icde", "kdd",
    "neurips", "icml", "iclr", "cvpr", "www", "geoinformatica", "ijgis",
    "transactions on", "acm", "ieee",
)


def norm(vals):
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return [0.5] * len(vals)
    return [(v - lo) / (hi - lo) for v in vals]


def main() -> int:
    ap = argparse.ArgumentParser(description="Rank survey candidate papers (composite score).")
    ap.add_argument("candidates", help="JSON list of candidate papers")
    ap.add_argument("--this-year", type=int, default=dt.date.today().year,
                    help="reference year for recency")
    ap.add_argument("--top", type=int, default=0, help="print only the top N (0 = all)")
    ap.add_argument("--json", metavar="PATH", help="also write the ranked list as JSON")
    ap.add_argument("--strong-venue", action="append", default=[],
                    help="case-insensitive venue substring to treat as strong; repeatable")
    args = ap.parse_args()

    try:
        with open(args.candidates, encoding="utf-8") as fh:
            papers = json.load(fh)
        if isinstance(papers, dict):
            papers = papers.get("papers") or papers.get("results") or []
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR cannot read {args.candidates}: {exc}", file=sys.stderr)
        return 1
    if not papers:
        print("ERROR no candidates", file=sys.stderr)
        return 1

    cites = norm([math.log1p(max(0, p.get("citation_count", 0) or 0)) for p in papers])
    centr = norm([max(0, p.get("n_citers_in_set", 0) or 0) for p in papers])
    rec = norm([-(args.this_year - (p.get("year") or args.this_year)) for p in papers])
    venue_hints = tuple(s.lower() for s in (args.strong_venue or DEFAULT_STRONG_VENUE_HINTS))
    for i, p in enumerate(papers):
        venue = (p.get("venue") or "").lower()
        vbump = 1.0 if any(s in venue for s in venue_hints) else 0.4
        survey = 1 if (p.get("is_survey") or "survey" in (p.get("title") or "").lower()
                       or "review" in (p.get("title") or "").lower()) else 0
        p["score"] = round(0.45 * cites[i] + 0.25 * centr[i] + 0.20 * rec[i]
                           + 0.10 * vbump + 0.05 * survey, 3)
        if survey:
            p["why"] = "survey/review — orienting overview"
        elif cites[i] > 0.8:
            p["why"] = "seminal / most-cited in area"
        elif rec[i] > 0.8:
            p["why"] = "recent — near state of the art"
        elif centr[i] > 0.6:
            p["why"] = "central — widely cited within this set"
        else:
            p["why"] = "relevant supporting work"

    papers.sort(key=lambda p: -p["score"])
    shown = papers[:args.top] if args.top else papers
    print(f"Ranked reading list ({len(shown)} of {len(papers)}):\n")
    for i, p in enumerate(shown, 1):
        cc = p.get("citation_count")
        print(f"{i:>2}. [{p['score']:.2f}] {p.get('title','(no title)')[:80]}")
        print(f"     {p.get('year','?')} · {p.get('venue','?')}"
              f"{f' · {cc} cites' if cc is not None else ''} — {p['why']}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(papers, fh, indent=2)
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
