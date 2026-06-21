---
name: find-papers
description: Searches scholarly literature with zero API keys across DBLP, Crossref, Semantic Scholar, and arXiv. Use when the user wants to find papers, search the literature, list a conference's proceedings (e.g. "all SIGSPATIAL 2025 papers"), survey related work on a topic, look up papers by author/venue/year, get DOIs or citation counts, or check recent arXiv preprints. Ships a venue-alias table that solves cross-API venue naming (DBLP "conf/gis" vs Semantic Scholar "SIGSPATIAL/GIS" vs Crossref proceedings titles) plus polite, cached, 429-resilient search scripts. Trigger words - find papers, literature search, related work, proceedings, DBLP, Crossref, Semantic Scholar, arXiv, citation count, DOI lookup, venue search.
---

# Find Papers

Key-free scholarly search. Produces verified paper metadata — titles, authors,
year, venue, DOIs/arXiv ids, citation counts, open-access PDF links — from
four free APIs, with the venue-name translation layer that makes cross-API
search actually work. Serves the literature-review and related-work stages;
feeds `fetch-paper` (full text) and `verify-citations` (bibliography gate).

## When to use

- "Find papers about X" / "survey related work on X"
- "List everything published at <venue> <year>"
- "What are the most-cited papers on X?" / "look up this DOI"
- "What's new on arXiv about X?"
- Another skill (literature-review, draft-related-work, study-exemplars,
  select-venue) needs real papers to ground its output

## Inputs

- A topic, author, venue, year, DOI, or arXiv id (any combination)
- `CONTACT_EMAIL` env var — required by every script (polite-pool identity);
  scripts prompt interactively if unset, or exit 1 with instructions
- Optional: `S2_API_KEY` env var for reliable Semantic Scholar access
- Optional: a venue profile `venues/conferences/<id>.yml` (schema in
  `venues/schema.yml`) — its `aliases:` block is the authoritative
  venue-name mapping

## Provider cheat sheet

| Need | Provider | Script |
|---|---|---|
| Enumerate a CS venue-year ("all KDD 2025 papers") | DBLP | `dblp_search.py` |
| DOI-backed metadata, publisher filters, date ranges | Crossref | `crossref_search.py` |
| Abstracts, citation counts, OA PDF links, topic search | Semantic Scholar | `s2_search.py` |
| Preprints, newest work, full-text HTML links | arXiv | `arxiv_search.py` |

Details, rate limits, and the fallback matrix: [references/api-notes.md](references/api-notes.md).

## Process

1. **Resolve the venue identity first** (skip for pure topic searches).
   Venue names differ across every API and a wrong string silently returns
   zero results. Resolution order:
   - `venues/conferences/<id>.yml` → `aliases:` block (dblp_key, s2_venue,
     crossref_container), if a profile exists;
   - otherwise [references/venue-aliases.md](references/venue-aliases.md)
     (~20 top venues, with per-venue gotchas: SIGSPATIAL = `conf/gis`,
     VLDB = `journals/pvldb` by *volume*, post-2023 SIGMOD = PACMMOD,
     NeurIPS toc rename, ICLR/ICML absent from Crossref...);
   - otherwise discover live: `python3 scripts/dblp_search.py --find-venue
     "<name>"`, then follow "Adding or re-verifying a venue" in
     venue-aliases.md.
   When a venue profile supplied any fact the user will rely on (counts,
   coverage claims, deadlines mentioned alongside), re-verify against the
   profile's live `cfp_url` and the live APIs — profiles and alias tables
   go stale; the file itself says so.

2. **Ensure `CONTACT_EMAIL` is set.** Ask the user for their email if needed:
   `export CONTACT_EMAIL=you@university.edu`. Never invent one.

3. **Run the right script(s)** from the skill directory (all are Python 3
   stdlib-only; every one supports `--help`, `--json`, `--no-cache`):

   ```bash
   # Enumerate a venue-year (conference / journal volume / multi-volume toc)
   python3 scripts/dblp_search.py --key conf/gis --year 2025
   python3 scripts/dblp_search.py --key journals/pvldb --volume 18
   python3 scripts/dblp_search.py --toc db/conf/acl/acl2024-1.bht

   # Topic search with citation counts + OA PDFs (add --year to narrow)
   python3 scripts/s2_search.py --query "trajectory similarity learning" --limit 10

   # Venue search on S2 (exact venue string from the alias table!)
   python3 scripts/s2_search.py --venue "SIGSPATIAL/GIS" --year 2025

   # DOI-backed venue/date/type filtering
   python3 scripts/crossref_search.py --container SIGSPATIAL \
       --from-date 2025-01-01 --until-date 2025-12-31 --type proceedings-article

   # Fresh preprints
   python3 scripts/arxiv_search.py \
       --query 'cat:cs.DB AND abs:"spatial join"' --sort submittedDate
   ```

   Scripts enforce politeness themselves (1 req/s per host — 2s DBLP, 3s
   arXiv — UA with contact email, exponential 429 backoff, 24h cache under
   `.cache/find-papers/`, single-page fetches). Do not loop a script to
   paginate around its caps; refine the query instead.

4. **Cross-check and enrich.** Dedupe by DOI (fall back to normalized
   title+year). DBLP gives the authoritative venue list but no abstracts or
   citations — enrich interesting hits one at a time:
   `python3 scripts/s2_search.py --paper DOI:10.1145/3589132.3625571 --fields
   title,abstract,tldr,citationCount,openAccessPdf`. An arXiv hit is not an
   accepted paper — confirm venue acceptance via DBLP/Crossref before
   presenting it as one.

5. **Hand off.**
   - Full text needed → `fetch-paper` skill (Unpaywall/arXiv/ACM-OA, fetch
     on demand, processed transiently).
   - Results entering a bibliography or any written claim →
     `verify-citations` skill. Never emit a citation this skill did not
     actually retrieve.

## Output

A deduplicated result list presented as a markdown table (title, authors,
year, venue, DOI/arXiv id, citations, OA link) plus the exact script
commands used (so the search is reproducible). Use `--json` when piping into
files the user asked for. Report total counts vs. shown counts honestly;
when a provider failed (e.g. S2 429s exhausted), say so rather than filling
gaps from memory.

## References

- [references/venue-aliases.md](references/venue-aliases.md) — the alias
  table for ~20 top venues across all four APIs, per-venue gotchas,
  verification provenance, how to add a venue
- [references/api-notes.md](references/api-notes.md) — per-API operational
  notes, rate limits, licensing, fallback matrix

## Guardrails

- Never fabricate papers, DOIs, citation counts, or "I found N papers"
  claims — every presented result must come from an actual API response in
  this session. Route bibliography entries through `verify-citations`.
- Copyright: metadata is safe (DBLP is CC0, Crossref facts); abstracts and
  full text are fetched on demand and processed transiently — never commit
  them to the repo or bundle them in outputs. Attribute Semantic Scholar
  (ODC-BY) when its data is shown.
- Respect the baked-in rate limits; never bulk-crawl, never page through an
  entire corpus, never strip the contact email from requests.
- Never submit anything to any system on the user's behalf.
