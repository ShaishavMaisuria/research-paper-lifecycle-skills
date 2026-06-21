#!/usr/bin/env python3
"""Verify one exemplar paper and fetch its metadata (DBLP + Semantic Scholar).

Two jobs in an exemplar workflow:
  --title   verify that a claimed paper (e.g. a best-paper award listed on a
            venue's awards page) really exists: searches DBLP and flags
            exact-normalized title matches with venue, year, and DOI. An
            award claim is only "verified" when the award-page URL AND a
            DBLP match both exist — never present one from memory.
  --doi / --arxiv
            fetch one paper's metadata from Semantic Scholar: citation
            counts, external ids, and an open-access hint for the fetch step.

One identifier per invocation — never loop this script over a list for
bulk harvesting; exemplar sets are 5-8 papers, fetched one at a time.

Examples:
  python3 scripts/lookup_exemplar.py --title "Attention Is All You Need"
  python3 scripts/lookup_exemplar.py --title "Some Award Paper" --year 2023
  python3 scripts/lookup_exemplar.py --doi 10.1145/3589132.3625571
  python3 scripts/lookup_exemplar.py --arxiv 1706.03762 --json

Exit codes: 0 found; 3 no match (claim NOT verified); 2 bad input;
1 network failure. DBLP data is CC0; S2 data is ODC-BY (attribute S2).
"""
import argparse
import json
import re
import os
import sys
import urllib.parse

import polite_http as ph

DBLP_API = "https://dblp.org/search/publ/api"
S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = ("title,year,venue,authors,externalIds,citationCount,"
             "influentialCitationCount,openAccessPdf,publicationTypes")


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--title", metavar="TEXT",
                   help="paper title to verify against DBLP (exact title "
                        "from the award page)")
    p.add_argument("--year", metavar="YYYY",
                   help="with --title: restrict matches to this year")
    p.add_argument("--doi", metavar="DOI",
                   help="DOI for a Semantic Scholar metadata lookup")
    p.add_argument("--arxiv", metavar="ID",
                   help="arXiv id (e.g. 1706.03762) for an S2 metadata lookup")
    p.add_argument("--json", action="store_true",
                   help="emit results as JSON instead of text")
    p.add_argument("--no-cache", action="store_true",
                   help="bypass the response cache")
    args = p.parse_args()
    modes = [bool(args.title), bool(args.doi), bool(args.arxiv)]
    if sum(modes) != 1:
        p.error("provide exactly one of --title, --doi, or --arxiv")
    if args.year and not args.title:
        p.error("--year only applies to --title verification")
    if args.year and not re.fullmatch(r"\d{4}", args.year):
        p.error("--year must be YYYY")
    if args.doi and not args.doi.startswith("10."):
        p.error("--doi must be a bare DOI starting with 10. (no https://doi.org/ prefix)")
    return args


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def s2_headers():
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


def dblp_title_search(args):
    params = {"q": args.title, "format": "json", "h": "10"}
    url = f"{DBLP_API}?{urllib.parse.urlencode(params)}"
    body = ph.http_get(url, min_interval=2.0, use_cache=not args.no_cache)
    try:
        hits_obj = json.loads(body)["result"]["hits"]
    except (ValueError, KeyError):
        ph.fail("unexpected response from DBLP (not the expected JSON shape)")
    total = int(hits_obj.get("@total", 0))
    raw_hits = hits_obj.get("hit") or []
    if isinstance(raw_hits, dict):
        raw_hits = [raw_hits]

    wanted = norm_title(args.title)
    matches = []
    for h in raw_hits:
        info = h.get("info") or {}
        year = str(info.get("year", ""))
        if args.year and year != args.year:
            continue
        authors_field = ((info.get("authors") or {}).get("author")) or []
        if isinstance(authors_field, dict):
            authors_field = [authors_field]
        authors = [a.get("text", "") if isinstance(a, dict) else str(a)
                   for a in authors_field]
        matches.append({
            "title": info.get("title", "").rstrip("."),
            "exact_title_match": norm_title(info.get("title", "")) == wanted,
            "authors": authors,
            "venue": info.get("venue", ""),
            "year": year,
            "type": info.get("type", ""),
            "doi": info.get("doi", ""),
            "ee": info.get("ee", ""),
            "dblp_key": info.get("key", ""),
            "dblp_url": info.get("url", ""),
        })

    if not matches:
        scope = f" in year {args.year}" if args.year else ""
        ph.fail(
            f"no DBLP match for title \"{args.title}\"{scope} "
            f"(DBLP reported {total} total hits for the query). The claim is "
            "NOT verified: check the spelling against the award page, try "
            "without --year (camera-ready year can differ), or try a "
            "distinctive substring of the title. Do not present an award "
            "claim DBLP cannot corroborate.",
            3,
        )

    exact = [m for m in matches if m["exact_title_match"]]
    if args.json:
        json.dump({"query": args.title, "year_filter": args.year,
                   "dblp_total_hits": total, "exact_matches": len(exact),
                   "matches": matches}, sys.stdout, indent=2)
        print()
        return
    print(f"DBLP matches for \"{args.title}\""
          + (f" (year {args.year})" if args.year else "")
          + f": {len(matches)} shown / {total} total query hits, "
          f"{len(exact)} exact-normalized\n")
    for i, m in enumerate(matches, 1):
        flag = "EXACT" if m["exact_title_match"] else "fuzzy"
        authors = ", ".join(m["authors"][:3])
        if len(m["authors"]) > 3:
            authors += " et al."
        print(f"{i}. [{flag}] {m['title']} — {authors or '(authors n/a)'}")
        print(f"   {m['venue']} {m['year']} | type: {m['type']}"
              + (f" | doi:{m['doi']}" if m["doi"] else ""))
        if m["ee"]:
            print(f"   ee: {m['ee']}")
    print("\nVerification rule: an award claim needs the award-page URL AND "
          "an EXACT match above with the right venue/year. data: DBLP (CC0)")


def s2_lookup(args):
    pid = f"DOI:{args.doi}" if args.doi else f"ARXIV:{args.arxiv}"
    url = (f"{S2_BASE}/paper/{urllib.parse.quote(pid, safe=':/')}"
           f"?fields={urllib.parse.quote(S2_FIELDS)}")
    body = ph.http_get(url, headers=s2_headers(), use_cache=not args.no_cache,
                       none_on_404=True)
    if body is None:
        ph.fail(
            f"Semantic Scholar has no record for {pid}. Check the identifier; "
            "very new papers can lag in S2 — fall back to a DBLP --title "
            "lookup or Crossref via the find-papers skill.",
            3,
        )
    try:
        rec = json.loads(body)
    except ValueError:
        ph.fail("unexpected response from Semantic Scholar (not JSON)")
    if args.json:
        rec["_oa_hint"] = oa_hint(rec)
        json.dump(rec, sys.stdout, indent=2)
        print()
        return
    authors = ", ".join(a.get("name", "") for a in (rec.get("authors") or [])[:6])
    if len(rec.get("authors") or []) > 6:
        authors += " et al."
    ext = rec.get("externalIds") or {}
    print(f"{rec.get('title', '(untitled)')} — {authors or '(authors n/a)'} "
          f"({rec.get('year', '?')})")
    print(f"  venue: {rec.get('venue') or 'n/a'} | "
          f"types: {','.join(rec.get('publicationTypes') or []) or 'n/a'}")
    print(f"  ids: " + (" | ".join(x for x in (
        f"doi:{ext['DOI']}" if ext.get("DOI") else "",
        f"arXiv:{ext['ArXiv']}" if ext.get("ArXiv") else "",
    ) if x) or "(none)"))
    print(f"  citations: {rec.get('citationCount', 'n/a')} "
          f"(influential: {rec.get('influentialCitationCount', 'n/a')})")
    print(f"  OA: {oa_hint(rec)}")
    print("\ndata: Semantic Scholar Academic Graph (ODC-BY; attribute S2)")


def main():
    args = parse_args()
    if args.title:
        dblp_title_search(args)
    else:
        s2_lookup(args)


if __name__ == "__main__":
    main()
