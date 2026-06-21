#!/usr/bin/env python3
"""Search the arXiv API (free, no key) for preprints. Atom XML in, records out.

arXiv etiquette REQUIRES a 3-second gap between requests — this script
enforces it (persisted across invocations). arXiv has no conference-venue
concept; find venue papers via category + keywords or jr: (journal-ref).

Query syntax (field prefixes): ti: au: abs: cat: jr: all:  with AND/OR/ANDNOT,
quoted phrases, and submittedDate ranges.

Examples:
  python3 scripts/arxiv_search.py --query 'cat:cs.DB AND abs:"spatial join"' --max-results 10
  python3 scripts/arxiv_search.py --query 'all:"trajectory prediction" AND submittedDate:[202605010000 TO 202606112359]' --sort submittedDate
  python3 scripts/arxiv_search.py --id 1607.00653
  python3 scripts/arxiv_search.py --query 'au:Hinton AND cat:cs.LG' --show-abstract

Requires CONTACT_EMAIL (or interactive prompt) for a polite User-Agent.
"""
import argparse
import json
import sys
import urllib.parse
import xml.etree.ElementTree as ET

import polite_http as ph

API = "https://export.arxiv.org/api/query"
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "os": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}
SORTS = {"relevance": "relevance", "submittedDate": "submittedDate",
         "lastUpdatedDate": "lastUpdatedDate"}


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--query", metavar="EXPR",
                      help="arXiv search_query expression (ti:/au:/abs:/cat:/jr:/all:)")
    mode.add_argument("--id", metavar="IDS", dest="id_list",
                      help="comma-separated arXiv ids, e.g. 1607.00653,2310.06825 (max 10)")
    p.add_argument("--max-results", type=int, default=10,
                   help="results per request (default 10, max 100; single request, "
                        "never pages)")
    p.add_argument("--start", type=int, default=0, help="result offset (default 0)")
    p.add_argument("--sort", choices=sorted(SORTS), default="relevance",
                   help="sort order (descending)")
    p.add_argument("--show-abstract", action="store_true",
                   help="also print abstracts (displayed transiently; never commit "
                        "abstracts to a repo)")
    p.add_argument("--json", action="store_true",
                   help="emit simplified records as JSON instead of text")
    p.add_argument("--no-cache", action="store_true", help="bypass the response cache")
    args = p.parse_args()
    if not 1 <= args.max_results <= 100:
        p.error("--max-results must be between 1 and 100 (politeness cap)")
    if args.id_list and len(args.id_list.split(",")) > 10:
        p.error("--id accepts at most 10 ids per call (politeness cap)")
    return args


def text(el, path):
    node = el.find(path, NS)
    return " ".join(node.text.split()) if node is not None and node.text else ""


def record_of(entry) -> dict:
    arxiv_id = text(entry, "a:id").rsplit("/abs/", 1)[-1]
    cats = [c.get("term", "") for c in entry.findall("a:category", NS)]
    pdf = ""
    for link in entry.findall("a:link", NS):
        if link.get("title") == "pdf":
            pdf = link.get("href", "")
    return {
        "title": text(entry, "a:title"),
        "authors": [text(a, "a:name") for a in entry.findall("a:author", NS)],
        "arxiv_id": arxiv_id,
        "published": text(entry, "a:published")[:10],
        "updated": text(entry, "a:updated")[:10],
        "primary_category": (lambda n: n.get("term", "") if n is not None else "")(
            entry.find("arxiv:primary_category", NS)),
        "categories": cats,
        "doi": text(entry, "arxiv:doi"),
        "journal_ref": text(entry, "arxiv:journal_ref"),
        "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
        "html_url": f"https://arxiv.org/html/{arxiv_id}",
        "pdf_url": pdf or f"https://arxiv.org/pdf/{arxiv_id}",
        "abstract": text(entry, "a:summary"),
    }


def main():
    args = parse_args()
    params = {"start": str(args.start), "max_results": str(args.max_results)}
    if args.id_list:
        params["id_list"] = args.id_list
    else:
        params["search_query"] = args.query
        params["sortBy"] = SORTS[args.sort]
        params["sortOrder"] = "descending"
    url = f"{API}?{urllib.parse.urlencode(params)}"

    # arXiv asks for >= 3 seconds between API calls.
    body = ph.http_get(url, min_interval=3.0, use_cache=not args.no_cache)
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        ph.fail("unexpected response from arXiv (not parseable Atom XML)")

    total = int(text(root, "os:totalResults") or 0)
    entries = root.findall("a:entry", NS)
    # arXiv reports query errors as a single entry titled "Error"
    if entries and text(entries[0], "a:title") == "Error":
        ph.fail(f"arXiv rejected the query: {text(entries[0], 'a:summary')}")
    records = [record_of(e) for e in entries]
    if not args.show_abstract:
        for r in records:
            r.pop("abstract", None)

    if args.json:
        json.dump({"total": total, "results": records}, sys.stdout, indent=2)
        print()
        return
    if not records:
        print(f"0 results (totalResults={total}). Check the field prefixes "
              "(ti:/abs:/cat:) and quoting — see --help examples.")
        return
    print(f"total matches: {total} (showing {len(records)})\n")
    for i, r in enumerate(records, 1):
        authors = ", ".join(r["authors"][:6]) or "(authors n/a)"
        if len(r["authors"]) > 6:
            authors += " et al."
        print(f"{i}. {r['title']} — {authors}")
        meta = " | ".join(x for x in (
            f"arXiv:{r['arxiv_id']}", r["primary_category"],
            f"submitted:{r['published']}",
            f"doi:{r['doi']}" if r["doi"] else "",
            f"jref:{r['journal_ref']}" if r["journal_ref"] else "",
        ) if x)
        print(f"   {meta}")
        print(f"   abs:{r['abs_url']} | html:{r['html_url']} | pdf:{r['pdf_url']}")
        if args.show_abstract and r.get("abstract"):
            print(f"   abstract: {r['abstract']}")


if __name__ == "__main__":
    main()
