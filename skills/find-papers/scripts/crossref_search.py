#!/usr/bin/env python3
"""Search Crossref works (no API key; mailto= polite pool) for DOI metadata.

Use for: DOI-backed venue enumeration (ACM/IEEE proceedings, journals),
bibliographic lookups, citation counts (is-referenced-by-count).
NOT useful for: ICLR / ICML / NeurIPS (no Crossref DOIs) or modern EDBT
(DataCite DOIs) — see references/venue-aliases.md.

Examples:
  python3 scripts/crossref_search.py --container SIGSPATIAL \
      --from-date 2025-01-01 --until-date 2025-12-31 --type proceedings-article
  python3 scripts/crossref_search.py --query "learned index structures" --rows 5
  python3 scripts/crossref_search.py --container "Proceedings of the VLDB Endowment" \
      --from-date 2025-01-01 --rows 20

Requires CONTACT_EMAIL (or interactive prompt) — sent as mailto= and in the
User-Agent, which puts requests in Crossref's more reliable polite pool.
"""
import argparse
import json
import sys
import urllib.parse

import polite_http as ph

WORKS_API = "https://api.crossref.org/works"
SELECT = "DOI,title,container-title,author,issued,type,is-referenced-by-count,publisher"


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--container", metavar="TITLE",
                   help="query.container-title substring (proceedings/journal title; "
                        "see references/venue-aliases.md for the right string)")
    p.add_argument("--query", metavar="TEXT", help="free bibliographic query")
    p.add_argument("--from-date", metavar="YYYY-MM-DD", help="filter from-pub-date")
    p.add_argument("--until-date", metavar="YYYY-MM-DD", help="filter until-pub-date")
    p.add_argument("--type", metavar="TYPE", dest="work_type",
                   help="Crossref work type, e.g. proceedings-article, journal-article")
    p.add_argument("--rows", type=int, default=20,
                   help="results per request (default 20, max 100; this script "
                        "never cursor-crawls)")
    p.add_argument("--json", action="store_true",
                   help="emit simplified records as JSON instead of text")
    p.add_argument("--no-cache", action="store_true", help="bypass the response cache")
    args = p.parse_args()
    if not args.container and not args.query:
        p.error("provide --container and/or --query")
    if not 1 <= args.rows <= 100:
        p.error("--rows must be between 1 and 100 (politeness cap)")
    return args


def year_of(item: dict) -> str:
    parts = (item.get("issued") or {}).get("date-parts") or [[None]]
    return str(parts[0][0]) if parts[0] and parts[0][0] else ""


def record_of(item: dict) -> dict:
    authors = []
    for a in item.get("author", []) or []:
        name = " ".join(x for x in (a.get("given"), a.get("family")) if x)
        if name or a.get("name"):
            authors.append(name or a.get("name"))
    titles = item.get("title") or [""]
    containers = item.get("container-title") or [""]
    return {
        "title": titles[0],
        "authors": authors,
        "container": containers[0],
        "year": year_of(item),
        "type": item.get("type", ""),
        "doi": item.get("DOI", ""),
        "cited_by": item.get("is-referenced-by-count", 0),
        "publisher": item.get("publisher", ""),
    }


def main():
    args = parse_args()
    params = {"rows": str(args.rows), "select": SELECT,
              "mailto": ph.contact_email()}
    if args.container:
        params["query.container-title"] = args.container
    if args.query:
        params["query.bibliographic"] = args.query
    filters = []
    if args.from_date:
        filters.append(f"from-pub-date:{args.from_date}")
    if args.until_date:
        filters.append(f"until-pub-date:{args.until_date}")
    if args.work_type:
        filters.append(f"type:{args.work_type}")
    if filters:
        params["filter"] = ",".join(filters)

    url = f"{WORKS_API}?{urllib.parse.urlencode(params)}"
    body = ph.http_get(url, use_cache=not args.no_cache)
    try:
        msg = json.loads(body)["message"]
    except (ValueError, KeyError):
        ph.fail("unexpected response from Crossref (not the expected JSON shape)")
    total = msg.get("total-results", 0)
    items = [record_of(x) for x in msg.get("items", [])]

    if args.json:
        json.dump({"total": total, "results": items}, sys.stdout, indent=2)
        print()
        return
    if total == 0:
        print("0 works matched. For conferences, container titles vary by year — "
              "use the substring from references/venue-aliases.md, and note that "
              "ICLR/ICML/NeurIPS/modern-EDBT are NOT in Crossref.")
        return
    print(f"total matches: {total} (showing {len(items)}; refine filters rather "
          "than paging — this script never bulk-crawls)\n")
    for i, r in enumerate(items, 1):
        authors = ", ".join(r["authors"][:6]) or "(no authors listed)"
        if len(r["authors"]) > 6:
            authors += " et al."
        print(f"{i}. {r['title']} — {authors} ({r['year']})")
        print(f"   {r['container']} | doi:{r['doi']} | cited-by:{r['cited_by']}")


if __name__ == "__main__":
    main()
