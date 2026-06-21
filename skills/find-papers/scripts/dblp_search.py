#!/usr/bin/env python3
"""Search DBLP (CC0 metadata, no API key) — the best venue enumerator for CS.

Three modes (pick exactly one):
  --find-venue NAME      discover a venue's DBLP key (conf/gis, journals/pvldb...)
  --key KEY              enumerate one venue-year via a table-of-contents query
                         (combine with --year for conferences or --volume for
                         journals; or pass a raw --toc path instead of --key)
  --query TEXT           free-text publication search

Examples:
  python3 scripts/dblp_search.py --find-venue SIGSPATIAL
  python3 scripts/dblp_search.py --key conf/gis --year 2025          # 195 papers
  python3 scripts/dblp_search.py --key journals/pvldb --volume 17
  python3 scripts/dblp_search.py --toc db/conf/acl/acl2024-1.bht     # multi-volume venues
  python3 scripts/dblp_search.py --query "spatial join learned index" --max 10

Notes: DBLP has titles/authors/DOIs but NO abstracts and NO citation counts —
enrich by DOI via s2_search.py. Requires CONTACT_EMAIL (or interactive prompt).
"""
import argparse
import json
import sys
import urllib.parse

import polite_http as ph

PUBL_API = "https://dblp.org/search/publ/api"
VENUE_API = "https://dblp.org/search/venue/api"


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--find-venue", metavar="NAME",
                      help="search the venue index for NAME and print DBLP keys")
    mode.add_argument("--key", metavar="KEY",
                      help="DBLP venue key, e.g. conf/gis or journals/pvldb")
    mode.add_argument("--toc", metavar="PATH",
                      help="raw toc path, e.g. db/conf/acl/acl2024-1.bht")
    mode.add_argument("--query", metavar="TEXT", help="free-text publication search")
    p.add_argument("--year", type=int, help="with --key conf/...: edition year")
    p.add_argument("--volume", type=int, help="with --key journals/...: volume number")
    p.add_argument("--max", type=int, default=None, metavar="N",
                   help="max results to return (default: 30 for --query, "
                        "1000 for toc enumeration; hard cap 1000)")
    p.add_argument("--json", action="store_true",
                   help="emit simplified records as JSON instead of text")
    p.add_argument("--no-cache", action="store_true", help="bypass the response cache")
    return p.parse_args()


def hits_of(body: str):
    try:
        result = json.loads(body)["result"]
    except (ValueError, KeyError):
        ph.fail("unexpected response from DBLP (not the expected JSON shape)")
    hits = result.get("hits", {})
    total = int(hits.get("@total", 0))
    raw = hits.get("hit", [])
    if isinstance(raw, dict):
        raw = [raw]
    return total, raw


def author_names(info: dict) -> list:
    block = info.get("authors", {})
    authors = block.get("author", []) if isinstance(block, dict) else []
    if isinstance(authors, dict):
        authors = [authors]
    names = []
    for a in authors:
        if isinstance(a, dict):
            names.append(a.get("text", ""))
        else:
            names.append(str(a))
    return [n for n in names if n]


def record_of(hit: dict) -> dict:
    info = hit.get("info", {})
    title = info.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")
    return {
        "title": title.rstrip("."),
        "authors": author_names(info),
        "venue": info.get("venue", ""),
        "year": info.get("year", ""),
        "pages": info.get("pages", ""),
        "doi": info.get("doi", ""),
        "ee": info.get("ee", ""),
        "dblp_key": info.get("key", ""),
    }


def print_records(records: list, total: int, as_json: bool):
    if as_json:
        json.dump({"total": total, "results": records}, sys.stdout, indent=2)
        print()
        return
    print(f"total matches: {total} (showing {len(records)})\n")
    for i, r in enumerate(records, 1):
        authors = ", ".join(r["authors"]) or "(no authors listed)"
        line2 = "   " + " | ".join(
            x for x in (
                f"doi:{r['doi']}" if r["doi"] else "",
                f"ee:{r['ee']}" if r["ee"] else "",
                f"dblp:{r['dblp_key']}" if r["dblp_key"] else "",
            ) if x
        )
        print(f"{i}. {r['title']} — {authors} ({r['year']})")
        if line2.strip():
            print(line2)


def main():
    args = parse_args()
    use_cache = not args.no_cache

    if args.find_venue:
        q = urllib.parse.quote(args.find_venue)
        body = ph.http_get(f"{VENUE_API}?q={q}&format=json&h=15", min_interval=2.0, use_cache=use_cache)
        total, raw = hits_of(body)
        if total == 0:
            print(f"no DBLP venue matches '{args.find_venue}'")
            return
        out = []
        for hit in raw:
            info = hit.get("info", {})
            url = info.get("url", "")
            key = url.split("/db/", 1)[1].strip("/") if "/db/" in url else ""
            out.append({"venue": info.get("venue", ""), "acronym": info.get("acronym", ""),
                        "dblp_key": key, "url": url})
        if args.json:
            json.dump({"total": total, "results": out}, sys.stdout, indent=2)
            print()
        else:
            print(f"venue matches: {total} (showing {len(out)})\n")
            for i, v in enumerate(out, 1):
                acro = f" [{v['acronym']}]" if v.get("acronym") else ""
                print(f"{i}. {v['venue']}{acro}\n   key: {v['dblp_key']}   ({v['url']})")
        return

    if args.key or args.toc:
        if args.toc:
            toc = args.toc
        else:
            suffix = args.year if args.year is not None else args.volume
            if suffix is None:
                ph.fail("--key needs --year (conferences) or --volume (journals), "
                        "e.g. --key conf/gis --year 2025 or --key journals/pvldb --volume 17")
            basename = args.key.rstrip("/").rsplit("/", 1)[-1]
            toc = f"db/{args.key.strip('/')}/{basename}{suffix}.bht"
        h = min(args.max or 1000, 1000)
        q = urllib.parse.quote(f"toc:{toc}:")
        body = ph.http_get(f"{PUBL_API}?q={q}&format=json&h={h}", min_interval=2.0, use_cache=use_cache)
        total, raw = hits_of(body)
        if total == 0:
            print(f"0 papers for toc {toc} — the proceedings may not be indexed yet, "
                  "or the venue uses multi-volume tocs (try --toc db/.../"
                  f"{toc.rsplit('/', 1)[-1].replace('.bht', '')}-1.bht). "
                  "Verify the key with --find-venue.")
            return
        print_records([record_of(x) for x in raw], total, args.json)
        return

    # --query
    h = min(args.max or 30, 1000)
    q = urllib.parse.quote(args.query)
    body = ph.http_get(f"{PUBL_API}?q={q}&format=json&h={h}", min_interval=2.0, use_cache=use_cache)
    total, raw = hits_of(body)
    if total == 0:
        print(f"0 publications match '{args.query}'")
        return
    print_records([record_of(x) for x in raw], total, args.json)


if __name__ == "__main__":
    main()
