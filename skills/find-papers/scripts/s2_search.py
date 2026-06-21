#!/usr/bin/env python3
"""Search Semantic Scholar (key optional) — abstracts, citation counts, OA PDFs.

The anonymous shared pool 429s often; this script backs off exponentially.
For reliable access request a free key (semanticscholar.org/product/api) and
export S2_API_KEY — that grants a dedicated 1 req/s.

Modes (pick at least one of --venue/--query; --paper is exclusive):
  --venue STR [--year YYYY]   enumerate a venue (S2 venue string — NOT the
                              acronym; see references/venue-aliases.md, e.g.
                              SIGSPATIAL is "SIGSPATIAL/GIS")
  --query TEXT                relevance-ranked keyword search
  --paper ID                  one paper by DOI:10..../ARXIV:2310.01234/S2 id

Examples:
  python3 scripts/s2_search.py --venue "SIGSPATIAL/GIS" --year 2025 --limit 5
  python3 scripts/s2_search.py --query "trajectory similarity learning" --limit 10
  python3 scripts/s2_search.py --paper DOI:10.1145/3589132.3625571 --fields title,abstract,tldr,citationCount,openAccessPdf

S2 data is ODC-BY: attribute Semantic Scholar; do not redistribute abstracts
in bulk (display transiently, never commit them to a repo).
"""
import argparse
import json
import os
import sys
import urllib.parse

import polite_http as ph

BASE = "https://api.semanticscholar.org/graph/v1"
DEFAULT_FIELDS = "title,year,venue,authors,externalIds,citationCount,openAccessPdf"


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--venue", metavar="STR",
                   help="S2 canonical venue string (comma-separate for several)")
    p.add_argument("--year", metavar="YYYY", help="year or range, e.g. 2025 or 2023-2025")
    p.add_argument("--query", metavar="TEXT", help="keyword query")
    p.add_argument("--paper", metavar="ID",
                   help="single-paper lookup: DOI:10.x/..., ARXIV:2310.01234, or S2 sha")
    p.add_argument("--fields", default=DEFAULT_FIELDS,
                   help=f"comma-separated S2 fields (default: {DEFAULT_FIELDS})")
    p.add_argument("--limit", type=int, default=20,
                   help="max results to show (default 20, max 100; single page only, "
                        "never crawls continuation tokens)")
    p.add_argument("--json", action="store_true",
                   help="emit the parsed records as JSON instead of text")
    p.add_argument("--no-cache", action="store_true", help="bypass the response cache")
    args = p.parse_args()
    if not args.paper and not (args.venue or args.query):
        p.error("provide --venue and/or --query, or --paper ID")
    if args.paper and (args.venue or args.query):
        p.error("--paper cannot be combined with --venue/--query")
    if not 1 <= args.limit <= 100:
        p.error("--limit must be between 1 and 100")
    return args


def headers():
    h = {}
    key = os.environ.get("S2_API_KEY", "").strip()
    if key:
        h["x-api-key"] = key
    return h


def fmt_paper(r: dict, i: int = None):
    authors = ", ".join(a.get("name", "") for a in (r.get("authors") or [])[:6])
    if len(r.get("authors") or []) > 6:
        authors += " et al."
    ext = r.get("externalIds") or {}
    ids = " | ".join(x for x in (
        f"doi:{ext['DOI']}" if ext.get("DOI") else "",
        f"arXiv:{ext['ArXiv']}" if ext.get("ArXiv") else "",
    ) if x)
    oa = (r.get("openAccessPdf") or {}).get("url", "")
    prefix = f"{i}. " if i else ""
    print(f"{prefix}{r.get('title', '(untitled)')} — {authors or '(authors n/a)'} "
          f"({r.get('year', '?')})")
    meta = " | ".join(x for x in (
        r.get("venue", ""), ids,
        f"citations:{r['citationCount']}" if r.get("citationCount") is not None else "",
    ) if x)
    if meta:
        print(f"   {meta}")
    if oa:
        print(f"   OA PDF: {oa}  (verify the license at the source before reuse)")
    if r.get("abstract"):
        print(f"   abstract: {r['abstract']}")
    if r.get("tldr") and isinstance(r["tldr"], dict) and r["tldr"].get("text"):
        print(f"   tldr: {r['tldr']['text']}")


def main():
    args = parse_args()
    use_cache = not args.no_cache
    fields = urllib.parse.quote(args.fields)

    if args.paper:
        pid = urllib.parse.quote(args.paper, safe=":/")
        url = f"{BASE}/paper/{pid}?fields={fields}"
        body = ph.http_get(url, headers=headers(), use_cache=use_cache)
        try:
            rec = json.loads(body)
        except ValueError:
            ph.fail("unexpected response from Semantic Scholar (not JSON)")
        if args.json:
            json.dump(rec, sys.stdout, indent=2)
            print()
        else:
            fmt_paper(rec)
            print("\ndata: Semantic Scholar Academic Graph (ODC-BY; attribute S2)")
        return

    if args.venue:
        # /paper/search/bulk supports exact venue filtering (verified live:
        # venue=SIGSPATIAL/GIS&year=2025 -> 191 papers). Single page only.
        params = {"query": args.query or "*", "venue": args.venue,
                  "fields": args.fields}
        if args.year:
            params["year"] = args.year
        url = f"{BASE}/paper/search/bulk?{urllib.parse.urlencode(params)}"
    else:
        params = {"query": args.query, "fields": args.fields,
                  "limit": str(args.limit)}
        if args.year:
            params["year"] = args.year
        url = f"{BASE}/paper/search?{urllib.parse.urlencode(params)}"

    body = ph.http_get(url, headers=headers(), use_cache=use_cache)
    try:
        resp = json.loads(body)
    except ValueError:
        ph.fail("unexpected response from Semantic Scholar (not JSON)")
    total = resp.get("total", 0)
    data = (resp.get("data") or [])[: args.limit]

    if args.json:
        json.dump({"total": total, "results": data}, sys.stdout, indent=2)
        print()
        return
    if total == 0:
        hint = ""
        if args.venue:
            hint = (" — S2 venue strings are NOT acronyms (e.g. SIGSPATIAL is "
                    "'SIGSPATIAL/GIS', WWW is 'The Web Conference'); check "
                    "references/venue-aliases.md")
        print(f"0 papers matched{hint}")
        return
    print(f"total matches: {total} (showing {len(data)})\n")
    for i, r in enumerate(data, 1):
        fmt_paper(r, i)
    print("\ndata: Semantic Scholar Academic Graph (ODC-BY; attribute S2)")


if __name__ == "__main__":
    main()
