#!/usr/bin/env python3
"""Provider-agnostic resolver: fan out one search across the free indexes,
fail over gracefully, union the hits, and report coverage honestly.

Part of the find-papers skill (research-paper-skills). Python 3 stdlib only.

WHY THIS EXISTS
  Running a single search script collapses the whole result to one provider.
  If that provider (or any one of DBLP / Semantic Scholar / arXiv) is rate
  limited or unreachable, the pipeline silently narrows — dropping real,
  relevant papers for *provider* reasons, not relevance, and reporting the
  thin result as if it were complete. This orchestrator instead:

    * wraps each index lookup in try/except (via polite_http.http_try) so one
      outage degrades to the others rather than crashing or collapsing;
    * fans out across >= 2 independent indexes and UNIONS the hits;
    * dedupes on ANY stable identifier — a DOI is not required: an arXiv id,
      a DBLP key, or an ACL-Anthology id counts as a verifiable identifier
      (so DOI-less ML-proceedings papers are NOT discarded);
    * distinguishes "no verifiable identifier -> drop" from "provider down ->
      retry/fallback", and flags a candidate seen on only one index but not
      confirmed elsewhere as 'unresolved-keep' instead of dropping it;
    * emits a per-run provider-coverage report and stamps the run COMPLETE or
      PARTIAL — PARTIAL whenever any authoritative index was unreachable.

This is a copilot, not an autopilot: it never fabricates results, never
promises acceptance, and an arXiv-only hit is flagged as a preprint, not a
publication. Every record carries the provider(s) it actually came from.

EXAMPLES
  # Topic fan-out (S2 + arXiv + Crossref + DBLP), unioned and deduped:
  python3 scripts/resolve_papers.py --query "trajectory similarity learning"

  # Venue-year enumeration with failover (DBLP toc + S2 venue + Crossref):
  python3 scripts/resolve_papers.py --venue-year \
      --dblp-key conf/gis --year 2025 \
      --s2-venue "SIGSPATIAL/GIS" \
      --crossref-container "Advances in Geographic Information Systems"

  # Restrict the fan-out (e.g. skip S2 when you have no key and it 429s):
  python3 scripts/resolve_papers.py --query "learned index" --providers dblp,crossref,arxiv

Requires CONTACT_EMAIL (or interactive prompt). --json emits the full record
list plus the coverage report; the human view prints the coverage banner first.
"""
import argparse
import json
import re
import sys
import urllib.parse

import polite_http as ph

# Provider modules are siblings; import lazily-friendly names.
import dblp_search
import crossref_search
import s2_search
import arxiv_search

# The fan-out set is exactly the providers with adapters below (see ADAPTERS).
# OpenAlex is intentionally NOT here: it is key-gated and used only for the
# citation-graph edge stage (citation_graph.py), not venue/topic fan-out.


# --- identifier normalization -------------------------------------------------

def norm_doi(doi: str) -> str:
    d = (doi or "").strip().lower()
    for pre in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(pre):
            d = d[len(pre):]
    return d


def norm_arxiv(s: str) -> str:
    s = (s or "").strip().lower()
    m = re.search(r"arxiv\.org/(?:abs|pdf|html)/([^\s?#]+?)(?:\.pdf)?(?:$|[?#])", s)
    if m:
        s = m.group(1)
    s = re.sub(r"^arxiv:", "", s)
    s = re.sub(r"^10\.48550/arxiv\.", "", s)
    s = re.sub(r"v\d+$", "", s)  # drop version
    return s


def stable_ids(rec: dict) -> dict:
    """Extract every verifiable stable identifier from a unioned record.

    A DOI is NOT required. arXiv ids, DBLP keys and ACL-Anthology ids are all
    stable, citable identifiers; a record with any of them is keepable.
    """
    ids = {}
    if rec.get("doi"):
        ids["doi"] = norm_doi(rec["doi"])
    if rec.get("arxiv_id"):
        ids["arxiv"] = norm_arxiv(rec["arxiv_id"])
    if rec.get("dblp_key"):
        ids["dblp"] = rec["dblp_key"].strip().lower()
    # ACL Anthology DOIs use the 10.18653 prefix; also surface the bare id.
    doi = ids.get("doi", "")
    if doi.startswith("10.18653/"):
        ids["anthology"] = doi.split("/", 1)[1]
    return {k: v for k, v in ids.items() if v}


def has_verifiable_id(rec: dict) -> bool:
    return bool(stable_ids(rec))


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def dedupe_key(rec: dict) -> str:
    """Pick the strongest available identity key for union/dedupe.

    Prefers a real stable identifier; falls back to normalized title+year so
    that a DOI-less hit still merges with its arXiv/DBLP twin instead of being
    dropped for lack of a DOI.
    """
    ids = stable_ids(rec)
    for kind in ("doi", "arxiv", "anthology", "dblp"):
        if ids.get(kind):
            return f"{kind}:{ids[kind]}"
    title = norm_title(rec.get("title", ""))
    if title:
        return f"title:{title}|{rec.get('year', '')}"
    return ""


# --- per-provider adapters: each returns (records, status) -------------------
# Each adapter catches ProviderError and reports it via the ledger, returning
# [] so the union simply misses that provider rather than the run crashing.

def _blank(provider, rec):
    return {
        "title": rec.get("title", ""),
        "authors": rec.get("authors", []),
        "year": str(rec.get("year", "") or ""),
        "venue": rec.get("venue") or rec.get("container") or "",
        "doi": rec.get("doi", ""),
        "arxiv_id": rec.get("arxiv_id", ""),
        "dblp_key": rec.get("dblp_key", ""),
        "citations": rec.get("cited_by", rec.get("citationCount")),
        "oa_pdf": rec.get("oa_pdf", ""),
        "is_preprint": provider == "arxiv",
        "providers": [provider],
    }


def from_dblp(args, contact):
    """DBLP via http_try: topic query or venue toc."""
    try:
        if args.venue_year and args.dblp_key:
            basename = args.dblp_key.rstrip("/").rsplit("/", 1)[-1]
            toc = f"db/{args.dblp_key.strip('/')}/{basename}{args.year}.bht"
            q = urllib.parse.quote(f"toc:{toc}:")
            url = f"{dblp_search.PUBL_API}?q={q}&format=json&h=1000"
        elif args.query:
            q = urllib.parse.quote(args.query)
            url = f"{dblp_search.PUBL_API}?q={q}&format=json&h={args.limit}"
        else:
            return []
        body = ph.http_try(url, provider="DBLP", min_interval=2.0,
                           use_cache=not args.no_cache)
        total, raw = dblp_search.hits_of(body)
        recs = [_blank("dblp", dblp_search.record_of(h)) for h in raw]
        ph.note_provider("DBLP", "ok" if recs else "empty")
        return recs
    except ph.ProviderError as e:
        ph.note_provider("DBLP", "down", e.message)
        print(f"[failover] DBLP unavailable ({e.kind}); continuing with the "
              "other indexes.", file=sys.stderr)
        return []


def from_crossref(args, contact):
    try:
        params = {"rows": str(min(args.limit, 100)),
                  "select": crossref_search.SELECT, "mailto": contact}
        if args.venue_year and args.crossref_container:
            params["query.container-title"] = args.crossref_container
            params["filter"] = (f"from-pub-date:{args.year}-01-01,"
                                f"until-pub-date:{args.year}-12-31")
        elif args.query:
            params["query.bibliographic"] = args.query
        else:
            return []
        url = f"{crossref_search.WORKS_API}?{urllib.parse.urlencode(params)}"
        body = ph.http_try(url, provider="Crossref", use_cache=not args.no_cache)
        msg = json.loads(body)["message"]
        recs = [_blank("crossref", crossref_search.record_of(x))
                for x in msg.get("items", [])]
        ph.note_provider("Crossref", "ok" if recs else "empty")
        return recs
    except ph.ProviderError as e:
        ph.note_provider("Crossref", "down", e.message)
        print(f"[failover] Crossref unavailable ({e.kind}); continuing.",
              file=sys.stderr)
        return []
    except (ValueError, KeyError):
        ph.note_provider("Crossref", "down", "unexpected response shape")
        return []


def from_s2(args, contact):
    try:
        fields = s2_search.DEFAULT_FIELDS
        if args.venue_year and args.s2_venue:
            params = {"query": args.query or "*", "venue": args.s2_venue,
                      "fields": fields}
            if args.year:
                params["year"] = str(args.year)
            url = f"{s2_search.BASE}/paper/search/bulk?{urllib.parse.urlencode(params)}"
        elif args.query:
            params = {"query": args.query, "fields": fields,
                      "limit": str(args.limit)}
            url = f"{s2_search.BASE}/paper/search?{urllib.parse.urlencode(params)}"
        else:
            return []
        body = ph.http_try(url, provider="Semantic Scholar",
                           headers=s2_search.headers(), use_cache=not args.no_cache)
        resp = json.loads(body)
        out = []
        for r in (resp.get("data") or [])[: args.limit]:
            ext = r.get("externalIds") or {}
            out.append(_blank("s2", {
                "title": r.get("title", ""),
                "authors": [a.get("name", "") for a in (r.get("authors") or [])],
                "year": r.get("year", ""),
                "venue": r.get("venue", ""),
                "doi": ext.get("DOI", ""),
                "arxiv_id": ext.get("ArXiv", ""),
                "citationCount": r.get("citationCount"),
                "oa_pdf": (r.get("openAccessPdf") or {}).get("url", ""),
            }))
        ph.note_provider("Semantic Scholar", "ok" if out else "empty")
        return out
    except ph.ProviderError as e:
        ph.note_provider("Semantic Scholar", "down", e.message)
        print(f"[failover] Semantic Scholar unavailable ({e.kind}); continuing. "
              "(A free S2_API_KEY makes this far less likely.)", file=sys.stderr)
        return []
    except ValueError:
        ph.note_provider("Semantic Scholar", "down", "unexpected response shape")
        return []


def from_arxiv(args, contact):
    if not args.query:
        return []  # arXiv has no venue concept; only meaningful for topics
    try:
        params = {"search_query": args.query, "start": "0",
                  "max_results": str(min(args.limit, 100)),
                  "sortBy": "relevance", "sortOrder": "descending"}
        url = f"{arxiv_search.API}?{urllib.parse.urlencode(params)}"
        body = ph.http_try(url, provider="arXiv", min_interval=3.0,
                           use_cache=not args.no_cache)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(body)
        out = []
        for e in root.findall("a:entry", arxiv_search.NS):
            r = arxiv_search.record_of(e)
            out.append(_blank("arxiv", {
                "title": r["title"], "authors": r["authors"],
                "year": (r["published"] or "")[:4],
                "venue": r.get("journal_ref", "") or "arXiv (preprint)",
                "doi": r.get("doi", ""), "arxiv_id": r["arxiv_id"],
                "oa_pdf": r["pdf_url"],
            }))
        ph.note_provider("arXiv", "ok" if out else "empty")
        return out
    except ph.ProviderError as e:
        ph.note_provider("arXiv", "down", e.message)
        print(f"[failover] arXiv unavailable ({e.kind}); continuing.",
              file=sys.stderr)
        return []
    except Exception:
        ph.note_provider("arXiv", "down", "unexpected response shape")
        return []


ADAPTERS = {
    "dblp": from_dblp,
    "crossref": from_crossref,
    "s2": from_s2,
    "arxiv": from_arxiv,
}


# --- union, dedupe, resolution state -----------------------------------------

def merge(into: dict, other: dict) -> None:
    """Fold `other` into `into`, keeping the richest field from either."""
    into["providers"] = sorted(set(into["providers"]) | set(other["providers"]))
    for f in ("doi", "arxiv_id", "dblp_key", "venue", "oa_pdf"):
        if not into.get(f) and other.get(f):
            into[f] = other[f]
    if into.get("citations") is None and other.get("citations") is not None:
        into["citations"] = other["citations"]
    if len(other.get("authors") or []) > len(into.get("authors") or []):
        into["authors"] = other["authors"]
    # A record is a preprint only if EVERY provider that saw it was arXiv.
    into["is_preprint"] = into["is_preprint"] and other["is_preprint"]


def resolve(records: list, consulted: list) -> list:
    """Union across providers, then assign a resolution state.

    Two-pass union so the SAME paper coming from different providers under
    different identifiers still merges (e.g. a Crossref DOI record and its
    arXiv-id twin): pass 1 clusters on the strongest stable id; pass 2 folds
    any record whose normalized title+year matches an existing cluster, so a
    DOI cluster and an arXiv cluster for one paper coalesce instead of
    double-counting — and a DOI-less hit is never dropped for lacking a DOI.

    States:
      resolved        seen with a verifiable id (DOI / arXiv / DBLP / anthology)
      unresolved-keep title-only match on a single index, no stable id yet, but
                      kept (not dropped) so a provider gap doesn't lose a paper
      drop            no verifiable identifier AND no usable title -> unusable
    """
    merged: dict = {}      # primary key (id or title) -> record
    title_index: dict = {}  # normalized title+year -> primary key
    dropped = 0

    def title_key(rec):
        t = norm_title(rec.get("title", ""))
        return f"{t}|{rec.get('year', '')}" if t else ""

    for rec in records:
        key = dedupe_key(rec)
        if not key:
            dropped += 1  # genuinely unusable: no id and no title
            continue
        tkey = title_key(rec)
        # If a cluster with the same title+year already exists, fold in there
        # even when the identifiers differ (cross-identifier merge).
        target = None
        if key in merged:
            target = key
        elif tkey and tkey in title_index:
            target = title_index[tkey]
        if target is not None:
            merge(merged[target], rec)
        else:
            merged[key] = rec
            if tkey:
                title_index.setdefault(tkey, key)

    out = []
    for rec in merged.values():
        if has_verifiable_id(rec):
            rec["resolution"] = "resolved"
        else:
            # title-only: keep it, flagged, and tell the agent how to confirm
            rec["resolution"] = "unresolved-keep"
            rec["resolution_note"] = (
                "no DOI/arXiv/DBLP id found yet; seen on "
                + ", ".join(rec["providers"])
                + ". Re-query the other indexes by exact title before citing — "
                "do NOT drop it for a single-index miss.")
        out.append(rec)
    # Stable, useful ordering: resolved first, then by citations desc, year desc
    out.sort(key=lambda r: (
        r["resolution"] != "resolved",
        -(r.get("citations") or 0),
        -int(r["year"]) if str(r.get("year", "")).isdigit() else 0,
    ))
    return out, dropped


# --- CLI ---------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--query", metavar="TEXT",
                   help="topic / keyword query, fanned out across indexes")
    p.add_argument("--venue-year", action="store_true",
                   help="venue-year enumeration mode (supply --year and any of "
                        "--dblp-key / --s2-venue / --crossref-container)")
    p.add_argument("--year", type=int, help="edition year (venue-year mode)")
    p.add_argument("--dblp-key", metavar="KEY", help="e.g. conf/gis")
    p.add_argument("--s2-venue", metavar="STR", help="exact S2 venue string")
    p.add_argument("--crossref-container", metavar="STR",
                   help="Crossref container-title substring")
    p.add_argument("--providers", default=",".join(ADAPTERS),
                   help="comma-separated subset to fan out across "
                        f"(default: {','.join(ADAPTERS)})")
    p.add_argument("--limit", type=int, default=25,
                   help="per-provider result cap (default 25, max 100)")
    p.add_argument("--json", action="store_true",
                   help="emit records + coverage report as JSON")
    p.add_argument("--no-cache", action="store_true", help="bypass the cache")
    args = p.parse_args()
    if not args.query and not args.venue_year:
        p.error("provide --query or --venue-year")
    if args.venue_year:
        if not args.year:
            p.error("--venue-year needs --year")
        if not (args.dblp_key or args.s2_venue or args.crossref_container):
            p.error("--venue-year needs at least one of --dblp-key / "
                    "--s2-venue / --crossref-container")
    chosen = [x.strip() for x in args.providers.split(",") if x.strip()]
    bad = [x for x in chosen if x not in ADAPTERS]
    if bad:
        p.error(f"unknown provider(s): {', '.join(bad)}; choose from {list(ADAPTERS)}")
    args.provider_list = chosen
    args.limit = max(1, min(args.limit, 100))
    return args


def main():
    args = parse_args()
    contact = ph.contact_email()

    all_records = []
    for name in args.provider_list:
        all_records.extend(ADAPTERS[name](args, contact))

    records, dropped = resolve(all_records, args.provider_list)
    report = ph.provider_report()

    answered = [p for p, v in report["providers"].items()
                if v["status"] in ("ok", "empty")]
    if len(answered) < 2:
        # Fewer than two independent indexes answered: a single survivor is
        # NOT a complete picture — say so loudly regardless of hit count.
        report["coverage"] = "PARTIAL"
        report["coverage_note"] = (
            f"only {len(answered)} index answered; need >= 2 independent "
            "indexes for a defensible 'complete' result.")

    if args.json:
        json.dump({
            "coverage": report["coverage"],
            "providers": report["providers"],
            "coverage_note": report.get("coverage_note", ""),
            "dropped_no_identifier": dropped,
            "count": len(records),
            "results": records,
        }, sys.stdout, indent=2)
        print()
        return

    banner = "COMPLETE" if report["coverage"] == "COMPLETE" else "PARTIAL"
    print(f"=== COVERAGE: {banner} ===")
    for prov, v in report["providers"].items():
        mark = {"ok": "answered", "empty": "answered (0 hits)",
                "degraded": "DEGRADED", "down": "UNREACHABLE"}.get(v["status"], v["status"])
        detail = f" — {v['detail']}" if v["detail"] else ""
        print(f"  {prov}: {mark}{detail}")
    if report["coverage"] == "PARTIAL":
        print("  ! PARTIAL: an authoritative index was unreachable. Real, "
              "relevant papers may be missing for PROVIDER reasons, not "
              "relevance. Retry later or add S2_API_KEY before claiming the "
              "search is exhaustive.")
    if report.get("coverage_note"):
        print(f"  ! {report['coverage_note']}")
    if dropped:
        print(f"  dropped {dropped} record(s) with no verifiable identifier "
              "AND no title (genuinely unusable).")
    print()

    print(f"{len(records)} unique paper(s) (unioned across "
          f"{', '.join(args.provider_list)}):\n")
    for i, r in enumerate(records, 1):
        authors = ", ".join(r["authors"][:6]) or "(authors n/a)"
        if len(r["authors"]) > 6:
            authors += " et al."
        flag = ""
        if r["resolution"] == "unresolved-keep":
            flag = "  [unresolved-keep]"
        if r["is_preprint"]:
            flag += "  [preprint — confirm acceptance via DBLP/Crossref]"
        print(f"{i}. {r['title']} — {authors} ({r['year']}){flag}")
        ids = " | ".join(x for x in (
            f"doi:{r['doi']}" if r["doi"] else "",
            f"arXiv:{r['arxiv_id']}" if r["arxiv_id"] else "",
            f"dblp:{r['dblp_key']}" if r["dblp_key"] else "",
        ) if x) or "(no stable id yet)"
        meta = " | ".join(x for x in (
            r["venue"], ids,
            f"citations:{r['citations']}" if r["citations"] is not None else "",
            f"via:{'+'.join(r['providers'])}",
        ) if x)
        print(f"   {meta}")
        if r.get("resolution_note"):
            print(f"   note: {r['resolution_note']}")
    if any("s2" in r["providers"] for r in records):
        print("\ndata includes Semantic Scholar (ODC-BY; attribute S2).")


if __name__ == "__main__":
    main()
