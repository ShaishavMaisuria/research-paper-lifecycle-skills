#!/usr/bin/env python3
"""Resolve a venue name/acronym to DBLP venue records (and optionally count
papers in one year's proceedings as a venue-size signal).

DBLP is the canonical, CC0, key-free registry of CS venues — the right place
to resolve "what is this venue's identity" when it has no profile under
venues/conferences/ yet. The returned `key` (e.g. conf/gis) is what the
venue-profile schema stores as `aliases.dblp_key`.

Subcommands:
  search <query>            venue search, e.g.  search "SIGSPATIAL"
  toc-count <key> <year>    count papers in one year's table of contents,
                            e.g.  toc-count conf/gis 2025
                            (single toc fetch — a polite venue-size proxy)

Politeness (required by this repo's rules):
  * <=1 request/second per host, exponential backoff on HTTP 429
  * User-Agent "research-paper-skills (mailto:$CONTACT_EMAIL)" — set the
    CONTACT_EMAIL env var (prompted for interactively if unset)
  * responses cached under .cache/ at the repo root (gitignored)
  * fetches single items only, never bulk crawls

Examples:
  CONTACT_EMAIL=you@example.org python3 scripts/dblp_venue_lookup.py search "SIGSPATIAL"
  python3 scripts/dblp_venue_lookup.py toc-count conf/gis 2025
  python3 scripts/dblp_venue_lookup.py toc-count conf/nips 2024 --bht db/conf/nips/neurips2024.bht
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DBLP_BASE = "https://dblp.org/search"
USER_AGENT_TMPL = "research-paper-skills (mailto:%s)"
MIN_INTERVAL_S = 1.0          # <=1 req/s per host
MAX_RETRIES = 4               # backoff: 2s, 4s, 8s, 16s on HTTP 429
CACHE_TTL_S = 24 * 3600       # search results: 1 day
CACHE_TTL_TOC_S = 7 * 24 * 3600  # historical tocs barely change: 7 days

_last_request_at = {}


def get_contact_email():
    email = os.environ.get("CONTACT_EMAIL", "").strip()
    if email:
        return email
    if sys.stdin.isatty():
        try:
            email = input(
                "CONTACT_EMAIL is not set. Enter a contact email to identify "
                "polite API traffic (stored nowhere, sent in User-Agent): "
            ).strip()
        except EOFError:
            email = ""
        if email:
            return email
    sys.exit(
        "error: CONTACT_EMAIL is not set. Set it so API operators can contact "
        "you instead of blocking you, e.g.\n"
        "  CONTACT_EMAIL=you@example.org python3 scripts/dblp_venue_lookup.py ..."
    )


def find_cache_dir():
    for start in (Path(__file__).resolve().parent, Path.cwd()):
        for anc in [start] + list(start.parents):
            if (anc / "venues").is_dir() or (anc / ".git").is_dir():
                d = anc / ".cache" / "select-venue"
                d.mkdir(parents=True, exist_ok=True)
                return d
    d = Path.cwd() / ".cache" / "select-venue"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _rate_limit(host):
    last = _last_request_at.get(host)
    if last is not None:
        wait = MIN_INTERVAL_S - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
    _last_request_at[host] = time.monotonic()


def fetch_json(url, email, ttl, refresh=False):
    cache_dir = find_cache_dir()
    cache_file = cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    if not refresh and cache_file.exists():
        try:
            entry = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - entry["fetched_at"] < ttl:
                return entry["body"], True
        except (ValueError, KeyError):
            pass  # corrupt cache entry — refetch

    host = urllib.parse.urlparse(url).netloc
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT_TMPL % email})
    delay = 2.0
    for attempt in range(MAX_RETRIES + 1):
        _rate_limit(host)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            cache_file.write_text(
                json.dumps({"fetched_at": time.time(), "url": url, "body": body}),
                encoding="utf-8",
            )
            return body, False
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES:
                print("HTTP 429 from %s — backing off %.0fs (attempt %d/%d)"
                      % (host, delay, attempt + 1, MAX_RETRIES), file=sys.stderr)
                time.sleep(delay)
                delay *= 2
                continue
            sys.exit("error: HTTP %s from %s — %s" % (e.code, url, e.reason))
        except urllib.error.URLError as e:
            sys.exit("error: could not reach %s — %s" % (url, e.reason))
        except json.JSONDecodeError:
            sys.exit("error: non-JSON response from %s" % url)
    sys.exit("error: still rate-limited by %s after %d retries" % (host, MAX_RETRIES))


def cmd_search(args, email):
    url = "%s/venue/api?%s" % (
        DBLP_BASE,
        urllib.parse.urlencode({"q": args.query, "format": "json", "h": args.max}),
    )
    body, cached = fetch_json(url, email, CACHE_TTL_S, refresh=args.refresh)
    hits = (body.get("result", {}).get("hits", {}) or {}).get("hit", []) or []
    results = []
    for h in hits:
        info = h.get("info", {})
        v_url = info.get("url", "")
        m = re.search(r"/db/((?:conf|journals|series)/[^/]+)", v_url)
        results.append({
            "venue": info.get("venue"),
            "acronym": info.get("acronym"),
            "type": info.get("type"),
            "dblp_key": m.group(1) if m else None,
            "url": v_url,
        })
    out = {"query": args.query, "from_cache": cached, "results": results}
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print("DBLP venue search %r — %d hit(s)%s"
              % (args.query, len(results), " [cached]" if cached else ""))
        for r in results:
            print("  %-16s %-28s %s" % (r["dblp_key"] or "?", r["acronym"] or "-", r["venue"]))
            print("  %-16s %s" % ("", r["url"]))
        if not results:
            print("  No DBLP venue matched. Try the full name, a different "
                  "acronym, or search at https://dblp.org/search?q=" )
    return 0


def cmd_toc_count(args, email):
    if args.bht:
        bht = args.bht
    else:
        base = args.key.rstrip("/").split("/")[-1]
        bht = "db/%s/%s%d.bht" % (args.key, base, args.year)
    q = "toc:%s:" % bht
    url = "%s/publ/api?%s" % (
        DBLP_BASE,
        urllib.parse.urlencode({"q": q, "format": "json", "h": 1}),
    )
    body, cached = fetch_json(url, email, CACHE_TTL_TOC_S, refresh=args.refresh)
    total = int((body.get("result", {}).get("hits", {}) or {}).get("@total", 0))
    out = {"dblp_key": args.key, "year": args.year, "bht": bht,
           "paper_count": total, "from_cache": cached}
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print("%s %d: %d paper(s) in DBLP toc %s%s"
              % (args.key, args.year, total, bht, " [cached]" if cached else ""))
        if total == 0:
            print("  0 hits usually means the toc filename differs from the key "
                  "(e.g. conf/nips uses neurips2024.bht for recent years) or the "
                  "proceedings are not indexed yet. Find the exact .bht name on "
                  "https://dblp.org/db/%s/ and pass it with --bht." % args.key)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Polite DBLP venue lookup (stdlib only, cached, rate-limited).",
        epilog="DBLP metadata is CC0. Requires CONTACT_EMAIL for the User-Agent.",
    )
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    ap.add_argument("--refresh", action="store_true", help="bypass the .cache/ entry")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search", help="search DBLP venues by name/acronym")
    sp.add_argument("query", help='venue name or acronym, e.g. "SIGSPATIAL"')
    sp.add_argument("--max", type=int, default=10, help="max hits (default 10)")

    tp = sub.add_parser("toc-count", help="count papers in one year's proceedings toc")
    tp.add_argument("key", help="DBLP venue key, e.g. conf/gis")
    tp.add_argument("year", type=int, help="proceedings year, e.g. 2025")
    tp.add_argument("--bht", help="explicit toc path when it differs from "
                                  "db/<key>/<basename><year>.bht")

    args = ap.parse_args(argv)
    email = get_contact_email()
    if args.cmd == "search":
        return cmd_search(args, email)
    return cmd_toc_count(args, email)


if __name__ == "__main__":
    sys.exit(main())
