#!/usr/bin/env python3
"""Rank a venue-year window's papers by citation count (Semantic Scholar).

Builds the "top-cited" half of an exemplar set: ONE polite request to the
S2 /paper/search/bulk endpoint enumerates the venue-year window (up to
1,000 papers with citation counts), then this script ranks locally and
prints the top N with DOIs and open-access hints. It never paginates.

The venue string must be S2's canonical name, NOT the acronym
(SIGSPATIAL is "SIGSPATIAL/GIS"; WWW is "The Web Conference"). Take it
from the `aliases.s2_venue` field of venues/conferences/<id>.yml
(--venue-profile reads it for you) or from the find-papers skill's
venue-aliases table.

Citation counts favor older papers: rank a window ending 2-3 years back
(e.g. --year 2020-2023), never the current proceedings year.

Examples:
  python3 scripts/rank_top_cited.py --venue "SIGSPATIAL/GIS" --year 2023 --top 10
  python3 scripts/rank_top_cited.py \\
      --venue-profile venues/conferences/sigspatial-2026.yml \\
      --year 2020-2023 --top 8 --json

Exit codes: 0 ranked results; 2 bad input; 3 the venue-year matched zero
papers (a wrong S2 venue string is the usual cause); 1 network failure.
S2 data is ODC-BY: attribute Semantic Scholar; never commit abstracts.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse

import polite_http as ph

BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = ("title,year,venue,authors,externalIds,citationCount,"
          "influentialCitationCount,openAccessPdf,publicationTypes")


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--venue", metavar="STR",
                   help='S2 canonical venue string, e.g. "SIGSPATIAL/GIS"')
    p.add_argument("--venue-profile", metavar="PATH",
                   help="venues/conferences/<id>.yml — reads aliases.s2_venue")
    p.add_argument("--year", metavar="YYYY[-YYYY]", required=True,
                   help="proceedings year or range, e.g. 2023 or 2020-2023")
    p.add_argument("--top", type=int, default=10,
                   help="how many top-cited papers to print (default 10, max 50)")
    p.add_argument("--min-citations", type=int, default=0, metavar="N",
                   help="drop papers below N citations (default 0)")
    p.add_argument("--json", action="store_true",
                   help="emit the ranked records as JSON instead of text")
    p.add_argument("--no-cache", action="store_true",
                   help="bypass the response cache")
    args = p.parse_args()
    if bool(args.venue) == bool(args.venue_profile):
        p.error("provide exactly one of --venue or --venue-profile")
    if not re.fullmatch(r"\d{4}(-\d{4})?", args.year):
        p.error("--year must be YYYY or YYYY-YYYY")
    if not 1 <= args.top <= 50:
        p.error("--top must be between 1 and 50")
    return args


def alias_from_profile(path: str, key: str = "s2_venue") -> str:
    """Minimal line-based extraction of an aliases.<key> value from a venue
    profile YAML (stdlib only — no yaml module). Fails clearly when the
    key is missing or null."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as e:
        ph.fail(f"cannot read venue profile {path}: {e}", 2)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            val = stripped.split(":", 1)[1]
            val = val.split(" #", 1)[0].strip().strip('"').strip("'")
            if val and val.lower() != "null":
                return val
            ph.fail(
                f"`{key}` is null/empty in {path} — find the S2 venue string "
                "(find-papers references/venue-aliases.md or live DBLP/S2 "
                "discovery) and pass it via --venue", 2)
    ph.fail(f"no `{key}:` line found in {path} — is this a venue profile "
            "following venues/schema.yml?", 2)
    raise AssertionError("unreachable")


def headers():
    h = {}
    key = os.environ.get("S2_API_KEY", "").strip()
    if key:
        h["x-api-key"] = key
    return h


def oa_hint(rec: dict) -> str:
    oa = (rec.get("openAccessPdf") or {}).get("url", "")
    if oa:
        return f"{oa}  (verify license at source)"
    ext = rec.get("externalIds") or {}
    doi = ext.get("DOI", "")
    if doi.startswith("10.1145/"):
        return (f"https://dl.acm.org/doi/pdf/{doi}  (ACM DL open access since "
                "Jan 2026; open in a browser — blocks scripted downloads)")
    if ext.get("ArXiv"):
        return f"https://arxiv.org/abs/{ext['ArXiv']}  (preprint — may differ from camera-ready)"
    return "none from S2 — resolve via the fetch-paper skill (Unpaywall)"


def main():
    args = parse_args()
    venue = args.venue or alias_from_profile(args.venue_profile)
    params = {"query": "*", "venue": venue, "year": args.year, "fields": FIELDS}
    url = f"{BASE}/paper/search/bulk?{urllib.parse.urlencode(params)}"
    body = ph.http_get(url, headers=headers(), use_cache=not args.no_cache)
    try:
        resp = json.loads(body)
    except ValueError:
        ph.fail("unexpected response from Semantic Scholar (not JSON)")

    total = resp.get("total", 0)
    data = resp.get("data") or []
    if total == 0:
        ph.fail(
            f'venue "{venue}" with year {args.year} matched 0 papers on '
            "Semantic Scholar. The S2 venue string is probably wrong — it is "
            "NOT the acronym (SIGSPATIAL is 'SIGSPATIAL/GIS', WWW is 'The "
            "Web Conference'). Check the venue profile aliases or the "
            "find-papers skill's references/venue-aliases.md, and sanity-"
            "check with a DBLP toc count for the same year.",
            3,
        )

    ranked = sorted(
        data,
        key=lambda r: (r.get("citationCount") or 0,
                       r.get("influentialCitationCount") or 0),
        reverse=True,
    )
    ranked = [r for r in ranked
              if (r.get("citationCount") or 0) >= args.min_citations]
    top = ranked[: args.top]

    notes = []
    if total > len(data):
        notes.append(
            f"venue-year window has {total} papers but S2 returned one bulk "
            f"page of {len(data)} — ranking covers that page only; narrow "
            "the year window for a complete ranking."
        )
    this_year = datetime.date.today().year
    max_year = max(int(y) for y in args.year.split("-"))
    if max_year >= this_year - 1:
        notes.append(
            f"window includes {max_year}: citation counts for the last two "
            "proceedings years are near zero and not a quality signal — "
            "prefer best-paper awards for recent years."
        )

    if args.json:
        json.dump(
            {"venue": venue, "year": args.year, "total_in_window": total,
             "ranked_shown": len(top), "notes": notes, "results": top,
             "attribution": "Semantic Scholar Academic Graph (ODC-BY)"},
            sys.stdout, indent=2)
        print()
        return

    print(f"venue: {venue} | years: {args.year} | papers in window: {total} "
          f"| showing top {len(top)} by citations\n")
    for i, r in enumerate(top, 1):
        authors = ", ".join(a.get("name", "") for a in (r.get("authors") or [])[:3])
        if len(r.get("authors") or []) > 3:
            authors += " et al."
        ext = r.get("externalIds") or {}
        ids = " | ".join(x for x in (
            f"doi:{ext['DOI']}" if ext.get("DOI") else "",
            f"arXiv:{ext['ArXiv']}" if ext.get("ArXiv") else "",
        ) if x)
        cites = r.get("citationCount") or 0
        infl = r.get("influentialCitationCount") or 0
        ptypes = ",".join(r.get("publicationTypes") or []) or "n/a"
        print(f"{i:2d}. [{cites} cites | {infl} influential] "
              f"{r.get('title', '(untitled)')} — {authors or '(authors n/a)'} "
              f"({r.get('year', '?')})")
        print(f"     {ids or '(no DOI/arXiv id)'} | types: {ptypes}")
        print(f"     OA: {oa_hint(r)}")
    for n in notes:
        print(f"\nNOTE: {n}")
    print("\ndata: Semantic Scholar Academic Graph (ODC-BY; attribute S2); "
          f"counts are a snapshot as of {datetime.date.today().isoformat()}")


if __name__ == "__main__":
    main()
