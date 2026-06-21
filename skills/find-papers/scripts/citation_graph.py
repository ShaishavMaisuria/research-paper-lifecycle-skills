#!/usr/bin/env python3
"""Expand a seed set along the citation graph — the recall stage keyword
search cannot reach. Python 3 stdlib only, no API key.

A topic/keyword pass saturates: it keeps returning the same on-topic hits and
systematically misses (a) foundational/seminal anchors the sub-area is built
on, (b) direct competitors that share citers but not your query keywords, and
(c) shared-infrastructure dependencies every paper in the field cites but none
names in a topic query. Those are reached by edges, not by words.

Given a handful of on-topic SEED papers (DOIs, OpenAlex/arXiv ids, or titles),
this pulls both directions of the citation graph and re-ranks the neighbors by
how many seeds touch each one (co-citation / co-reference frequency), so the
high-degree neighbors the keyword pass missed float to the top:

  references-of  (seed -> what it cites)   surfaces shared anchors + infra deps
  cited-by       (seed <- what cites it)   surfaces competitors + newer work

Providers (both answer key-free in the polite mailto pool, verified 2026-06):
  - OpenAlex: both edge directions + cited_by_count, batch id resolution.
  - Crossref: references-of via the work's `reference` array (DOI fallback).

Examples:
  # mixed seeds: two DOIs and a bare title
  python3 scripts/citation_graph.py \
      --seed DOI:10.14778/3551793.3551844 \
      --seed "Denoising Diffusion Probabilistic Models" --top 25

  # references-of only (find the anchors + infra a cluster stands on)
  python3 scripts/citation_graph.py --seed DOI:10.x/abc --direction refs

  # seeds from a prior search piped in as JSON {"results":[{doi/ title}, ...]}
  python3 scripts/resolve_papers.py --query "<topic>" --json | \
      python3 scripts/citation_graph.py --seeds-json - --top 30

This is a recall aid, not a citation source. Every surfaced neighbor is a
CANDIDATE: confirm venue/acceptance via dblp/crossref and route anything
entering a bibliography through verify-citations. Never present a neighbor as
"found" or cited without that confirmation.

Requires CONTACT_EMAIL (or interactive prompt) — sent as mailto= and in the
User-Agent for both providers' polite pools.
"""
import argparse
import json
import sys
import urllib.parse

import polite_http as ph

OA_BASE = "https://api.openalex.org/works"
CR_BASE = "https://api.crossref.org/works"
# OpenAlex batch filter caps at 50 ids per request; stay under it.
OA_BATCH = 25
# how many cited-by neighbors to pull per seed (one polite page, no crawling)
CITEDBY_PER_SEED = 50


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--seed", action="append", default=[], metavar="ID|TITLE",
                   help="a seed paper: DOI:10.x/..., openalex:W..., arXiv:2310.01234, "
                        "or a free-text title (repeatable; 2-8 on-topic seeds work best)")
    p.add_argument("--seeds-json", metavar="PATH",
                   help="read seeds from a JSON file (or - for stdin) shaped like the "
                        "--json output of the other scripts: {\"results\":[{\"doi\"|"
                        "\"title\": ...}, ...]} or a bare list of strings")
    p.add_argument("--direction", choices=("both", "refs", "citedby"), default="both",
                   help="which edges to follow (default both). refs = what seeds cite "
                        "(anchors/infra); citedby = what cites seeds (competitors/new)")
    p.add_argument("--top", type=int, default=25,
                   help="how many re-ranked neighbors to show (default 25)")
    p.add_argument("--min-degree", type=int, default=1,
                   help="drop neighbors fewer than this many seeds touch (default 1; "
                        "raise to 2+ to keep only cross-seed hubs)")
    p.add_argument("--json", action="store_true",
                   help="emit the ranked neighbor records as JSON")
    p.add_argument("--no-cache", action="store_true", help="bypass the response cache")
    args = p.parse_args()
    if not args.seed and not args.seeds_json:
        p.error("provide at least one --seed, or --seeds-json PATH")
    if args.top < 1:
        p.error("--top must be >= 1")
    return args


def load_json_seeds(path: str) -> list:
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    try:
        data = json.loads(raw)
    except ValueError:
        ph.fail(f"--seeds-json {path!r} is not valid JSON")
    items = data.get("results", data) if isinstance(data, dict) else data
    seeds = []
    for it in items or []:
        if isinstance(it, str):
            seeds.append(it)
        elif isinstance(it, dict):
            ident = (it.get("doi") or it.get("openalex")
                     or it.get("arxiv_id") or it.get("arxiv") or it.get("title"))
            if ident:
                seeds.append(f"DOI:{ident}" if it.get("doi") and not str(ident).startswith("DOI:") else ident)
    if not seeds:
        ph.fail("--seeds-json contained no usable seeds (need doi/openalex/arxiv/title)")
    return seeds


def oa_get(path_or_query: str, *, use_cache: bool) -> dict:
    """GET an OpenAlex URL (full url already built) and parse JSON."""
    body = ph.http_get(path_or_query, use_cache=use_cache)
    try:
        return json.loads(body)
    except ValueError:
        ph.fail("unexpected response from OpenAlex (not JSON)")


def resolve_seed(seed: str, email: str, *, use_cache: bool) -> dict | None:
    """Resolve a seed (DOI / openalex id / arXiv id / title) to an OpenAlex work.

    Returns {id, title, doi, year} or None if unresolvable.
    """
    s = seed.strip()
    select = "id,title,doi,publication_year,referenced_works,cited_by_count"
    low = s.lower()
    work_url = None
    if low.startswith("doi:") or "doi.org/" in low or s.startswith("10."):
        doi = s.split("doi.org/", 1)[-1]
        doi = doi[4:] if doi.lower().startswith("doi:") else doi
        work_url = f"{OA_BASE}/doi:{urllib.parse.quote(doi, safe='/')}"
    elif low.startswith("openalex:") or low.startswith("w") and s[1:].isdigit():
        wid = s.split(":", 1)[-1]
        work_url = f"{OA_BASE}/{wid}"
    elif low.startswith("arxiv:"):
        arx = s.split(":", 1)[-1]
        work_url = f"{OA_BASE}/arxiv:{urllib.parse.quote(arx)}"

    if work_url:
        url = f"{work_url}?{urllib.parse.urlencode({'select': select, 'mailto': email})}"
        rec = oa_get(url, use_cache=use_cache)
        if rec.get("id"):
            return rec
        # fall through to title search if the id form did not resolve

    # title search
    q = urllib.parse.urlencode(
        {"filter": f"title.search:{s}", "per-page": "1", "select": select, "mailto": email}
    )
    res = oa_get(f"{OA_BASE}?{q}", use_cache=use_cache)
    hits = res.get("results") or []
    return hits[0] if hits else None


def wid(work: dict) -> str:
    return (work.get("id") or "").rsplit("/", 1)[-1]


def batch_resolve(ids: list, email: str, *, use_cache: bool) -> dict:
    """Resolve a list of OpenAlex work ids to metadata, OA_BATCH at a time."""
    out = {}
    for i in range(0, len(ids), OA_BATCH):
        chunk = [x for x in ids[i : i + OA_BATCH] if x]
        if not chunk:
            continue
        q = urllib.parse.urlencode(
            {"filter": "ids.openalex:" + "|".join(chunk), "per-page": str(len(chunk)),
             "select": "id,title,doi,publication_year,cited_by_count", "mailto": email}
        )
        res = oa_get(f"{OA_BASE}?{q}", use_cache=use_cache)
        for w in res.get("results") or []:
            out[wid(w)] = w
    return out


def crossref_refs(doi: str, email: str, *, use_cache: bool) -> list:
    """references-of via Crossref: DOIs embedded in the work's `reference` array.

    Key-free fallback for the refs direction — invoked when a DOI-bearing seed
    carries no `referenced_works` on OpenAlex. Returns referenced DOIs
    (lowercased), or [] on any provider failure. NON-FATAL by design: the
    fallback is best-effort, so a Crossref miss (e.g. an arXiv/DataCite DOI not
    indexed by Crossref → 404) must not abort the whole run — use http_try, not
    http_get, and swallow ProviderError.
    """
    url = f"{CR_BASE}/{urllib.parse.quote(doi, safe='/')}?{urllib.parse.urlencode({'mailto': email})}"
    try:
        body = ph.http_try(url, provider="crossref", use_cache=use_cache)
    except ph.ProviderError:
        return []
    try:
        msg = json.loads(body).get("message", {})
    except ValueError:
        return []
    return [r["DOI"].lower() for r in (msg.get("reference") or []) if r.get("DOI")]


def dois_to_wids(dois: list, email: str, *, use_cache: bool) -> list:
    """Map a list of DOIs to OpenAlex work ids (OA_BATCH at a time).

    Lets the Crossref references-of fallback feed the WID-keyed degree machinery.
    """
    wids = []
    for i in range(0, len(dois), OA_BATCH):
        chunk = [d for d in dois[i : i + OA_BATCH] if d]
        if not chunk:
            continue
        q = urllib.parse.urlencode(
            {"filter": "doi:" + "|".join(chunk), "per-page": str(min(len(chunk), 50)),
             "select": "id", "mailto": email}
        )
        res = oa_get(f"{OA_BASE}?{q}", use_cache=use_cache)
        for w in res.get("results") or []:
            wids.append(wid(w))
    return wids


def seed_doi(work: dict) -> str:
    """Bare DOI of a resolved seed, or '' if it has none."""
    return (work.get("doi") or "").replace("https://doi.org/", "")


def main():
    args = parse_args()
    use_cache = not args.no_cache
    email = ph.contact_email()

    seeds = list(args.seed)
    if args.seeds_json:
        seeds += load_json_seeds(args.seeds_json)
    # de-dup while preserving order
    seeds = list(dict.fromkeys(s for s in seeds if s and s.strip()))

    print(f"resolving {len(seeds)} seed(s) on OpenAlex...", file=sys.stderr)
    resolved = []
    for s in seeds:
        rec = resolve_seed(s, email, use_cache=use_cache)
        if rec:
            resolved.append(rec)
            print(f"  seed: {(rec.get('title') or '?')[:60]} "
                  f"[{wid(rec)}]", file=sys.stderr)
        else:
            print(f"  unresolved (skipped): {s[:60]}", file=sys.stderr)
    if not resolved:
        ph.fail("no seeds resolved — check the DOIs/ids/titles. Titles must be "
                "specific enough that title.search returns the right paper.")

    seed_ids = {wid(r) for r in resolved}
    # neighbor_id -> {degree: # seeds touching it, dirs: set(), via: set()}
    degree: dict[str, dict] = {}

    def bump(nid: str, direction: str, src_title: str):
        if not nid or nid in seed_ids:
            return  # never rank a seed as its own neighbor
        d = degree.setdefault(nid, {"degree": 0, "dirs": set(), "via": []})
        d["degree"] += 1
        d["dirs"].add(direction)
        if len(d["via"]) < 3:
            d["via"].append(src_title[:40])

    for r in resolved:
        title = r.get("title") or "?"
        if args.direction in ("both", "refs"):
            refs = r.get("referenced_works") or []
            if not refs and seed_doi(r):
                # OpenAlex resolved the work but carries no reference list:
                # fall back to Crossref's `reference` array (key-free), then
                # map those DOIs to WIDs so they feed the degree machinery.
                cr_dois = crossref_refs(seed_doi(r), email, use_cache=use_cache)
                if cr_dois:
                    print(f"  refs via Crossref fallback for {wid(r)} "
                          f"({len(cr_dois)} refs)", file=sys.stderr)
                    refs = dois_to_wids(cr_dois, email, use_cache=use_cache)
            for ref in refs:
                bump(ref.rsplit("/", 1)[-1], "refs", title)
        if args.direction in ("both", "citedby"):
            q = urllib.parse.urlencode(
                {"filter": f"cites:{wid(r)}", "per-page": str(CITEDBY_PER_SEED),
                 "select": "id", "mailto": email}
            )
            res = oa_get(f"{OA_BASE}?{q}", use_cache=use_cache)
            for w in res.get("results") or []:
                bump(wid(w), "citedby", title)

    kept = {nid: d for nid, d in degree.items() if d["degree"] >= args.min_degree}
    if not kept:
        print(f"no neighbors met --min-degree {args.min_degree}; lower it or add seeds")
        return

    meta = batch_resolve(list(kept), email, use_cache=use_cache)

    ranked = []
    for nid, d in kept.items():
        m = meta.get(nid, {})
        ranked.append({
            "title": m.get("title") or "(title unresolved)",
            "year": m.get("publication_year"),
            "doi": (m.get("doi") or "").replace("https://doi.org/", ""),
            "openalex": nid,
            "global_citations": m.get("cited_by_count"),
            "seed_degree": d["degree"],
            "edges": sorted(d["dirs"]),
            "co_cited_with": d["via"],
        })
    # high co-citation degree first, then globally-influential anchors
    ranked.sort(key=lambda x: (x["seed_degree"], x["global_citations"] or 0), reverse=True)
    ranked = ranked[: args.top]

    if args.json:
        json.dump({"seeds_resolved": len(resolved), "neighbors_total": len(kept),
                   "results": ranked}, sys.stdout, indent=2)
        print()
        return

    print(f"\n{len(kept)} graph neighbor(s) across {len(resolved)} seed(s); "
          f"showing top {len(ranked)} by co-citation degree.")
    print("seed-degree = how many seeds touch this neighbor (the recall signal "
          "the keyword pass cannot see).\n")
    for i, r in enumerate(ranked, 1):
        tag = "+".join(r["edges"])
        ids = " | ".join(x for x in (
            f"doi:{r['doi']}" if r["doi"] else "", f"openalex:{r['openalex']}") if x)
        gc = r["global_citations"]
        print(f"{i}. {r['title']} ({r['year'] or '?'})")
        print(f"   seed-degree:{r['seed_degree']} [{tag}] | "
              f"global-citations:{gc if gc is not None else '?'} | {ids}")
    print("\ncandidates only — confirm venue/acceptance (dblp/crossref) and route "
          "any citation through verify-citations. Data: OpenAlex (CC0) + Crossref.")


if __name__ == "__main__":
    main()
