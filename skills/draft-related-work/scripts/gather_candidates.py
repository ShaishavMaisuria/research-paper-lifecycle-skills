#!/usr/bin/env python3
"""Build a clustering worksheet for Related Work from a list of identifiers.

Given DOIs and/or arXiv IDs of papers the user (or find-papers) actually
retrieved, fetch each paper's metadata ONE AT A TIME from Semantic Scholar
(title, year, venue, authors, citation count, abstract, tldr) and print a
worksheet with empty `cluster:` and `delta:` slots to fill during clustering.

This script never searches and never bulk-harvests: it resolves at most
25 known identifiers per run, one polite request per paper (<=1 req/s,
exponential backoff on 429, responses cached under .cache/, gitignored).
Requires CONTACT_EMAIL (prompts when unset on a TTY). Optional S2_API_KEY
gives a dedicated 1 req/s allowance instead of the flaky anonymous pool.

Examples:
  python3 scripts/gather_candidates.py 10.1145/3589132.3625571 arXiv:1706.03762
  python3 scripts/gather_candidates.py --from-file ids.txt --json

Output is TRANSIENT working material: it contains abstracts (Semantic
Scholar, ODC-BY). Read it, cluster, then discard — never commit it.
Identifiers that do not resolve are flagged (exit 3): treat them as
unverified and do NOT cite them until verify-citations clears them.
"""
import argparse
import json
import re
import sys

import polite_http as ph

BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,year,venue,authors,externalIds,citationCount,abstract,tldr"
MAX_IDS = 25  # politeness cap: this is a per-paper lookup tool, not a crawler

ARXIV_NEW = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
ARXIV_OLD = re.compile(r"^[a-z\-]+(\.[A-Za-z\-]+)?/\d{7}(v\d+)?$")


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("identifiers", nargs="*", metavar="ID",
                   help="DOI (10.xxxx/..., doi.org URL) or arXiv ID "
                        "(2403.12345, arXiv:2403.12345, arxiv.org URL)")
    p.add_argument("--from-file", metavar="FILE",
                   help="read additional identifiers from FILE, one per line "
                        "('#' comments and blank lines ignored)")
    p.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON instead of the worksheet")
    p.add_argument("--no-cache", action="store_true",
                   help="bypass the response cache")
    return p.parse_args()


def normalize(raw: str) -> str:
    """Map one user-supplied identifier to an S2 paper id (DOI:... / ARXIV:...).

    Returns "" when the token is not recognizable as a DOI or arXiv ID.
    """
    s = raw.strip().strip('.,;')
    if not s:
        return ""
    low = s.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi.org/", "doi:"):
        if low.startswith(prefix):
            s = s[len(prefix):]
            low = s.lower()
            break
    m = re.search(r"arxiv\.org/(?:abs|pdf|html)/([^\s?#]+?)(?:\.pdf)?$", low)
    if m:
        s = m.group(1)
        low = s.lower()
    if low.startswith("arxiv:"):
        s = s[6:]
        low = s.lower()
    # arXiv-issued DOIs alias the arXiv ID itself
    m = re.match(r"^10\.48550/arxiv\.(.+)$", low)
    if m:
        s = m.group(1)
        low = s.lower()
    if s.startswith("10.") and "/" in s:
        return f"DOI:{s}"
    if ARXIV_NEW.match(s) or ARXIV_OLD.match(low):
        return f"ARXIV:{s}"
    return ""


def collect_ids(args) -> list:
    raw = list(args.identifiers)
    if args.from_file:
        try:
            with open(args.from_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.split("#", 1)[0].strip()
                    if line:
                        raw.append(line)
        except OSError as e:
            ph.fail(f"cannot read --from-file {args.from_file}: {e}", code=2)
    if not raw:
        ph.fail("no identifiers given. Pass DOIs/arXiv IDs as arguments or "
                "via --from-file (see --help).", code=2)
    ids, bad = [], []
    for token in raw:
        norm = normalize(token)
        (ids if norm else bad).append(norm or token)
    if bad:
        ph.fail(
            "could not recognize as DOI or arXiv ID: "
            + ", ".join(repr(b) for b in bad)
            + "\nThis tool takes identifiers of papers you already found. "
            "For title/topic search, use the find-papers skill first.",
            code=2,
        )
    # dedupe, preserve order
    seen, unique = set(), []
    for i in ids:
        if i.lower() not in seen:
            seen.add(i.lower())
            unique.append(i)
    if len(unique) > MAX_IDS:
        ph.fail(
            f"{len(unique)} identifiers exceeds the politeness cap of "
            f"{MAX_IDS} per run. A Related Work section rarely needs more "
            "candidates than that at once — split into a second run if you "
            "must.", code=2,
        )
    return unique


def s2_headers() -> dict:
    import os
    key = os.environ.get("S2_API_KEY", "").strip()
    return {"x-api-key": key} if key else {}


def fetch_one(pid: str, use_cache: bool):
    import urllib.parse
    url = f"{BASE}/paper/{urllib.parse.quote(pid, safe=':/')}?fields={FIELDS}"
    try:
        body = ph.http_get(url, headers=s2_headers(), use_cache=use_cache,
                           tolerate=(404,))
    except ph.HttpStatusError:
        return None
    try:
        return json.loads(body)
    except ValueError:
        ph.fail("unexpected response from Semantic Scholar (not JSON)")


def worksheet_entry(i: int, pid: str, rec: dict) -> str:
    authors = ", ".join(a.get("name", "") for a in (rec.get("authors") or [])[:6])
    if len(rec.get("authors") or []) > 6:
        authors += " et al."
    ext = rec.get("externalIds") or {}
    ids = " | ".join(x for x in (
        f"doi:{ext['DOI']}" if ext.get("DOI") else "",
        f"arXiv:{ext['ArXiv']}" if ext.get("ArXiv") else "",
    ) if x) or pid
    lines = [
        f"## [{i}] {rec.get('title', '(untitled)')} ({rec.get('year', '?')})",
        f"- authors: {authors or '(n/a)'}",
        f"- venue: {rec.get('venue') or '(none listed — possibly preprint)'}",
        f"- ids: {ids}",
        f"- citations: {rec.get('citationCount', '?')}",
    ]
    tldr = rec.get("tldr") or {}
    if isinstance(tldr, dict) and tldr.get("text"):
        lines.append(f"- tldr: {tldr['text']}")
    if rec.get("abstract"):
        lines.append(f"- abstract: {rec['abstract']}")
    else:
        lines.append("- abstract: (not available from S2 — read it via "
                     "fetch-paper before clustering this one)")
    lines.append("- cluster: ____________________  <- fill in")
    lines.append("- delta vs our paper: ____________________  <- fill in")
    return "\n".join(lines)


def main():
    args = parse_args()
    ids = collect_ids(args)
    use_cache = not args.no_cache

    resolved, missing = [], []
    for pid in ids:
        rec = fetch_one(pid, use_cache)
        if rec is None:
            missing.append(pid)
            print(f"WARNING: {pid} not found in Semantic Scholar — verify the "
                  "identifier (verify-citations) before citing it.",
                  file=sys.stderr)
        else:
            resolved.append((pid, rec))

    if args.json:
        json.dump(
            {
                "resolved": [dict(rec, _requested_id=pid)
                             for pid, rec in resolved],
                "not_found": missing,
                "attribution": "Semantic Scholar Academic Graph (ODC-BY)",
                "transient": "contains abstracts — process transiently, "
                             "never commit",
            },
            sys.stdout, indent=2,
        )
        print()
    else:
        print(f"# Clustering worksheet — {len(resolved)} candidate(s)")
        print()
        print("> TRANSIENT working material (contains abstracts; Semantic "
              "Scholar, ODC-BY).")
        print("> Cluster, extract deltas, then discard. Never commit this "
              "output to the repo.")
        for i, (pid, rec) in enumerate(resolved, 1):
            print()
            print(worksheet_entry(i, pid, rec))
        if missing:
            print()
            print("## Unresolved identifiers — do NOT cite until verified")
            for pid in missing:
                print(f"- {pid}: not found in Semantic Scholar")

    if not resolved:
        ph.fail("none of the identifiers resolved — nothing to cluster.", code=3)
    if missing:
        sys.exit(3)


if __name__ == "__main__":
    main()
