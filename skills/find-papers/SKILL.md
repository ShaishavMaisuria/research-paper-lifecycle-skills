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
| **Fan out across the indexes, union, fail over, report coverage** | **all four** | **`resolve_papers.py`** |
| Expand a saturated seed set along citations (anchors, competitors, infra) | OpenAlex + Crossref | `citation_graph.py` |
| Pick the *canonical* instance of a named title (version drift / collision) | any (post-process) | `resolve_canonical.py` |

For any survey or venue enumeration you will present as reasonably complete,
**lead with `resolve_papers.py`**: it queries several indexes, unions the hits
deduped by *any* stable id (DOI, arXiv, DBLP, or anthology — a DOI is **not**
required), keeps going when one index is rate-limited or down, and stamps the
run COMPLETE or PARTIAL. Single-provider scripts are for one specific thing
(a DOI lookup, the canonical DBLP toc, fresh arXiv preprints) — never treat one
provider's silence as evidence a paper does not exist.

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
   # Provider-agnostic fan-out (PREFER for surveys / "is this complete?"):
   # unions DBLP+Crossref+S2+arXiv, fails over on any outage, prints a
   # COMPLETE/PARTIAL coverage banner.
   python3 scripts/resolve_papers.py --query "trajectory similarity learning"
   python3 scripts/resolve_papers.py --venue-year --year 2025 \
       --dblp-key conf/gis --s2-venue "SIGSPATIAL/GIS" \
       --crossref-container "Advances in Geographic Information Systems"

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

   # Expand a saturated seed set along the citation graph (see step 4)
   python3 scripts/citation_graph.py \
       --seed DOI:10.14778/3551793.3551844 --seed "<another on-topic title>" \
       --direction both --top 25
   ```

   Scripts enforce politeness themselves (1 req/s per host — 2s DBLP, 3s
   arXiv — UA with contact email, exponential 429 backoff, 24h cache under
   `.cache/find-papers/`, single-page fetches). Do not loop a script to
   paginate around its caps; refine the query instead.

4. **Cross-check, expand along the citation graph, and enrich.** Dedupe by
   *any* stable id, not DOI alone (DOI → arXiv id → DBLP key → ACL-anthology
   id), falling back to normalized title+year — `resolve_papers.py` does this
   union for you. **A missing DOI is not a reason to drop a paper**: real
   ML-proceedings work (ICLR/ICML/NeurIPS) and modern EDBT mint no Crossref
   DOI, yet their arXiv/DBLP/anthology ids are perfectly citable. Distinguish
   two failure modes that look alike but must be handled oppositely:
   *no verifiable identifier anywhere* → drop as unusable; *a provider was
   down / rate-limited* → that is **not** a "0 results" — re-query the paper on
   the other indexes and, if still unconfirmed, keep it flagged
   `unresolved-keep` rather than discarding it for a single-index miss.
   DBLP gives the authoritative venue list but no abstracts or citations —
   enrich interesting hits one at a time:
   `python3 scripts/s2_search.py --paper DOI:10.1145/3589132.3625571
   --fields title,abstract,tldr,citationCount,openAccessPdf`. An arXiv hit is
   not an accepted paper — confirm venue acceptance via DBLP/Crossref before
   presenting it as one.

   **Mandatory once the keyword/venue pass saturates** (a fresh query mostly
   returns papers you already have): topic search *systematically* misses
   three things that live one citation edge away — foundational/seminal
   anchors the sub-area is built on, direct competitors that share citers but
   not your keywords, and shared-infrastructure deps every paper cites but
   none names in a topic query. These are reached by edges, not words, and
   skipping this stage is the single largest driver of low recall. Take the
   top on-topic seeds and run the citation-graph expansion:

   ```bash
   python3 scripts/citation_graph.py --seed DOI:<seed1> --seed "<seed2 title>" \
       --direction both --top 25         # refs=anchors/infra, citedby=competitors
   ```

   It pulls both edge directions (references-of + cited-by) from OpenAlex
   (Crossref `reference` array as the key-free references fallback) and
   re-ranks neighbors by **co-citation degree** — how many seeds touch each —
   so high-degree hubs the keyword pass can't see float up. Then:
   - **Foundational/seminal anchor sweep**, per topical cluster: run
     `--direction refs`, read the top by global citations, and confirm every
     cluster has its obvious foundation (base model, canonical dataset,
     founding method) present — a recall hole if it doesn't.
   - **Cover the niche, not just the canon**: mine the brief's *distinctive
     mechanism noun-phrases* (the specific named technique/component/loss,
     not the generic topic words) into narrow targeted queries; feed new
     on-topic hits back in as seeds and re-expand.

   Every graph neighbor is a **candidate, not a result** — confirm
   venue/acceptance before presenting it, and surface *why* it surfaced
   (seed-degree, edges) so the user decides scope. Method and endpoints:
   [references/citation-graph-expansion.md](references/citation-graph-expansion.md).

5. **Resolve to the canonical instance — not just *a* match.** When the user
   named a specific paper (vs. a topic sweep), a relevance-ranked search will
   happily return an *adjacent* instance that passes a bare existence check
   but is the wrong citation: an older edition when a community-canonical
   successor exists (version/edition drift), or a different paper that shares
   a first author and a near-duplicate title (title collision). Before you
   present a single "the" paper, run the candidates through the guard:

   ```bash
   # pipe a title search straight in (works with any search script's --json)
   python3 scripts/s2_search.py --query "<the named title>" --json \
       | python3 scripts/resolve_canonical.py --stdin --title "<the named title>"
   ```

   It clusters near-duplicate titles, flags `[VERSION DRIFT]` and
   `[TITLE COLLISION]`, and marks a `PREFERRED` pick (latest canonical
   version for drift; highest impact / earliest seminal year for collisions)
   with a one-line `CHOOSE:` note. The PREFERRED pick is a *suggestion* —
   surface the siblings and let the user choose deliberately. Never silently
   collapse the cluster to one.

   When sibling records share a stable id but differ in surface title, the
   resolver emits `title_variants` (all distinct titles seen for that one
   work). **Match and dedupe on the stable id first, titles second** — an
   alternate title for the same DOI/eprint is an alias, not a different paper,
   and must never be scored as a miss. Once you pick the instance, **overwrite
   the entry's title field with the canonical string the API returned for that
   exact id**, not a recalled or hand-typed title, and keep the variants in a
   note so the chosen form is auditable. This is what stops a bib and a corpus
   from drifting to two different titles for the same work.

6. **Hand off.**
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

**Tag each result by evidence tier and keep titles canonical.** A result that
came only from a citation-graph edge or a single keyword hit is a *candidate*,
not a confirmed citation of any specific paper: label it (graph / keyword /
seed-degree) so a downstream consumer can threshold on confidence rather than
treat every entry as equally certain. When the target is a *known subset* of a
paper's bibliography, report recall against that subset separately from a
precision band against the expected full count — never present over-fetched
neighbors at the same confidence as confirmed hits. For every retained entry,
take the **title verbatim from the canonical record for its resolved id**
(don't hand-type or recall it), normalize to the publisher/DOI-canonical
capitalization, and wrap proper nouns/acronyms in braces in any BibTeX so the
as-published form survives — this is what prevents a title from fuzzy-matching
yet failing a strict string lookup.

**Always surface the coverage verdict.** When you fan out with
`resolve_papers.py`, repeat its COMPLETE/PARTIAL banner and the per-provider
status to the user. If the run is PARTIAL — any authoritative index was
unreachable or rate-limited — state plainly that the result is provisional and
real, relevant papers may be missing for *provider* reasons, not relevance;
offer to retry later or with `S2_API_KEY`. Never present a degraded run as if
it were an exhaustive search, and never silently narrow to the one provider
that happened to answer.

## References

- [references/venue-aliases.md](references/venue-aliases.md) — the alias
  table for ~20 top venues across all four APIs, per-venue gotchas,
  verification provenance, how to add a venue
- [references/api-notes.md](references/api-notes.md) — per-API operational
  notes, rate limits, licensing, the fallback matrix, and the
  provider-coverage / graceful-failover contract (`resolve_papers.py`)
- [references/citation-graph-expansion.md](references/citation-graph-expansion.md)
  — the citation-graph recall stage: edge directions, co-citation re-ranking,
  the foundational-anchor sweep, the claim-driven niche pass, key-free
  OpenAlex/Crossref endpoints

## Guardrails

- Never fabricate papers, DOIs, citation counts, or "I found N papers"
  claims — every presented result must come from an actual API response in
  this session. Route bibliography entries through `verify-citations`.
- Provider outage ≠ no result, and one surviving provider ≠ a complete search.
  When an index is down or rate-limited, fail over to the others (≥2
  independent indexes for any "complete" claim), keep an unconfirmed paper as
  `unresolved-keep` rather than dropping it on a single-index miss, and mark
  the run PARTIAL. A missing DOI is never grounds to discard a paper that has
  an arXiv / DBLP / anthology id. Never report a PARTIAL run as exhaustive.
- **A PARTIAL run is a retriable gate, not a finish line.** The scripts already
  retry 429/5xx with exponential backoff before giving up; if a run still comes
  back PARTIAL (a provider exhausted its retries), do NOT accept it as done
  because the surviving indexes "happened to cover" the targets — recall then
  rests on luck. Re-issue the failed leg after a cool-down (and with
  `S2_API_KEY` for Semantic Scholar), or substitute an equivalent provider,
  before declaring the pass complete. When a target was recoverable *only*
  through a fallback path, surface that title explicitly in provenance so the
  gap is auditable rather than silently absorbed.
- **Gate completion per required cluster, not just per run.** For any cluster
  the scope marks central (a direct-competitor or headline-contribution
  cluster), require that ≥2 independent indexes actually answered for *that*
  cluster's queries before treating it as covered; a central cluster confirmed
  by a single surviving provider is degraded, not complete, even if the overall
  run banner is COMPLETE.
- For a *named* paper, existence is not enough: an older edition or a
  same-author near-duplicate title can pass a bare match yet be the wrong
  citation. Run candidates through `resolve_canonical.py`, prefer the latest
  canonical version / higher-impact instance, and surface siblings so the
  user chooses — never auto-collapse to one without flagging it.
- Citation-graph neighbors (`citation_graph.py`) are recall *candidates*, not
  results: confirm venue/acceptance before presenting any, never count raw
  neighbors as "papers found," and surface the seed-degree/edge reason so the
  human decides scope rather than auto-including.
- Copyright: metadata is safe (DBLP is CC0, Crossref facts); abstracts and
  full text are fetched on demand and processed transiently — never commit
  them to the repo or bundle them in outputs. Attribute Semantic Scholar
  (ODC-BY) when its data is shown.
- Respect the baked-in rate limits; never bulk-crawl, never page through an
  entire corpus, never strip the contact email from requests.
- Never submit anything to any system on the user's behalf.
