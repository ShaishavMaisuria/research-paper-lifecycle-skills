# API Notes: DBLP, Crossref, Semantic Scholar, arXiv

Operational detail for the four key-free providers behind `find-papers`.
All facts below were verified live on 2026-06-11 unless marked otherwise.

## Table of contents

1. [Provider comparison](#provider-comparison)
2. [DBLP](#dblp)
3. [Crossref](#crossref)
4. [Semantic Scholar](#semantic-scholar)
5. [arXiv](#arxiv)
6. [Fallback matrix](#fallback-matrix)
7. [Canonical-instance resolution (version drift & title collisions)](#canonical-instance-resolution-version-drift--title-collisions)
8. [Politeness and licensing rails](#politeness-and-licensing-rails)
9. [Adjacent providers (when the big four are not enough)](#adjacent-providers)

## Provider comparison

| | DBLP | Crossref | Semantic Scholar | arXiv |
|---|---|---|---|---|
| API key | none | none | optional (`S2_API_KEY`) | none |
| Best at | CS venue enumeration | DOI metadata, publisher coverage | abstracts, citations, OA PDF links | preprints, latest work |
| Abstracts | no | rarely (publisher-dependent; ACM deposits none) | yes (most papers) | yes |
| Citation counts | no | `is-referenced-by-count` | `citationCount` | no |
| Venue concept | venue keys (`conf/gis`) | container-title strings | canonical venue strings | none |
| Data license | CC0 1.0 | facts, no claim asserted | ODC-BY (attribute; no bulk redistribution) | metadata free; paper licenses vary |
| Practical rate | ~1 req/2s (resets connections on bursts) | 50 req/s cap; be far politer | shared anon pool 429s often; 1 req/s with key | 1 req/3s (required etiquette) |

## DBLP

- Endpoints: `https://dblp.org/search/publ/api`, `/search/venue/api`,
  `/search/author/api`. Params: `q`, `format=json`, `h` (max 1000), `f`.
- **Killer feature — toc queries**: `q=toc:db/conf/<key>/<base><year>.bht:`
  enumerates one venue-year exactly. Verified: `db/conf/gis/gis2025.bht` →
  195 SIGSPATIAL 2025 papers with titles, authors, pages, DOIs, ee links.
- Journals use volume-numbered tocs (`db/journals/pvldb/pvldb17.bht` → 431
  papers). Some venues rename basenames mid-history (`nips2017.bht` →
  `neurips2018.bht`) or split into volumes (`acl2024-1.bht`) — see
  `venue-aliases.md`.
- Rate limiting is informal but real: bursts trigger HTTP 429 and then **raw
  TCP connection resets** for a minute or more. The scripts use a 2s
  per-host interval and treat resets as retryable; if you still get cut off,
  wait 60–90s.
- No abstracts, no citation counts: enrich by DOI through S2
  (`s2_search.py --paper DOI:<doi>`).
- Whole-venue XML also exists (`dblp.org/db/conf/gis/gis2025.xml`) but the
  search API JSON is easier to consume.

## Crossref

- Endpoint: `https://api.crossref.org/works`. No key. Allowed 50 req/s, but
  this skill stays at 1 req/s — there is no reason to go faster.
- **Polite pool**: include `mailto=<email>` and a UA with a mailto. Both are
  wired into `crossref_search.py` from `CONTACT_EMAIL`. Polite-pool traffic
  gets more reliable service and a warning before any block.
- Useful params: `query.container-title`, `query.bibliographic`,
  `filter=from-pub-date:...,until-pub-date:...,type:proceedings-article`,
  `rows` (≤1000; script caps at 100), `select=` to trim payloads.
  Deep paging via `cursor=*` exists — the script deliberately never uses it.
- Verified: `query.container-title=SIGSPATIAL` + 2025 date filter +
  `type:proceedings-article` → 130 works (main conference + co-located
  workshops, each under its own container title).
- Abstracts only when the publisher deposits them — ACM does not. Treat
  Crossref as the DOI/metadata backbone, not an abstract source.
- Coverage holes (verified): ICLR and ICML/PMLR mint no Crossref DOIs;
  modern EDBT DOIs are DataCite; modern NeurIPS has no DOIs at all.

## Semantic Scholar

- Base: `https://api.semanticscholar.org/graph/v1`. Key endpoints:
  `/paper/search` (relevance, `limit`≤100), `/paper/search/bulk` (exact
  filters: `venue=`, `year=`, up to 1000/page — the script reads ONE page,
  never follows continuation tokens), `/paper/{id}` where id can be
  `DOI:10...`, `ARXIV:2310.01234`, or an S2 sha.
- `fields=` controls the payload: `title,year,venue,authors,externalIds,
  citationCount,openAccessPdf,abstract,tldr,referenceCount,publicationVenue`.
- Verified: `search/bulk?query=*&venue=SIGSPATIAL/GIS&year=2025` → 191
  papers. Venue strings are canonical full names, never acronyms — see
  `venue-aliases.md`.
- **Rate limits are the #1 failure mode**: anonymous requests share a global
  pool and 429 readily (observed on the 3rd consecutive request during
  research). `s2_search.py` backs off exponentially (2s/4s/8s, honoring
  Retry-After). For real work, request a free key at
  semanticscholar.org/product/api#api-key-form and `export S2_API_KEY=...`
  for a dedicated 1 req/s.
- Licensing: ODC-BY 1.0 — attribute Semantic Scholar in outputs (the script
  prints the attribution line), never redistribute fetched abstracts in
  bulk, and treat each `openAccessPdf.url` as "verify license at source".
  Abstracts are missing for some publishers by agreement.

## arXiv

- Endpoint: `https://export.arxiv.org/api/query` (Atom 1.0 XML). No auth.
- **Etiquette: ≥3 seconds between calls** — enforced by `arxiv_search.py`
  even across consecutive invocations. Content updates daily, so cached
  responses (24h TTL) are perfectly fresh.
- Query syntax: prefixes `ti: au: abs: cat: jr: all:`; booleans
  `AND OR ANDNOT`; quoted phrases; date windows
  `submittedDate:[202501010000 TO 202512312359]`. Sort with
  `sortBy=submittedDate&sortOrder=descending` for "what's new".
- No venue concept — see the arXiv section of `venue-aliases.md`.
- Each result links: `arxiv.org/abs/<id>`, `arxiv.org/pdf/<id>`, and
  `arxiv.org/html/<id>` (native HTML for papers since Dec 2023; older ones
  via `ar5iv.labs.arxiv.org/html/<id>`) — HTML is the easiest full-text path
  for downstream skills.
- An arXiv preprint is NOT proof of publication; confirm acceptance via
  DBLP/Crossref before citing it as a venue paper (`externalIds` from S2
  link arXiv ids to DOIs).

## Fallback matrix

| Goal | First | Fallback | Last resort |
|---|---|---|---|
| Enumerate a CS venue-year | DBLP toc | S2 `--venue` | Crossref `--container` |
| Topic search w/ abstracts | S2 `--query` | arXiv `--query` | Crossref `--query` |
| Citation counts | S2 | Crossref `is-referenced-by-count` | — |
| DOI → metadata | Crossref | S2 `--paper DOI:` | DBLP `--query` by title |
| Latest preprints | arXiv (sort submittedDate) | S2 (year filter) | — |
| OA PDF link | S2 `openAccessPdf` | Unpaywall (see `fetch-paper` skill) | arXiv pdf/html |

| Resolve a *named* title to its canonical instance | `resolve_canonical.py` over the candidate `--json` | manual: prefer latest version / highest cites | — |

Notes: ACM has NO public API — DBLP/Crossref carry its metadata, and since
Jan 1 2026 the whole ACM DL is open access (`dl.acm.org/doi/pdf/<doi>`,
single fetches only; bulk crawling stays banned by ACM ToU). OpenAlex still
answers key-free in the polite `mailto` pool (verified 2026-06) and powers
the citation-graph recall stage below; profiles also record `openalex_source`
ids. Its ACM proceedings *venue* mapping stays unreliable
(`primary_location.source` often null) — keep enumerating venues via DBLP and
use OpenAlex for edges, not venue lists.

## Graceful failover and provider coverage (`resolve_papers.py`)

The fallback matrix above tells you which provider to *try next*. The failure
that matrix does not prevent is **silent narrowing**: when DBLP / Semantic
Scholar / arXiv are rate-limited or unreachable, a single-provider pass (or a
script that crashes mid-pipeline) collapses the whole result to whichever
index still answers — usually Crossref or DBLP+Crossref — dropping real,
relevant papers for *provider* reasons, not relevance, and presenting the thin
result as if it were exhaustive. `resolve_papers.py` is the provider-agnostic
orchestrator that closes that gap. The contract it enforces (and that any
multi-provider flow should follow):

1. **Wrap every index lookup in try/except** — built on `polite_http.http_try`,
   which raises `ProviderError` instead of exiting. One outage degrades to the
   others; it never crashes the run and never collapses it silently.
2. **Fan out across ≥2 independent indexes and UNION the hits** (DBLP +
   Crossref + Semantic Scholar + arXiv; OpenAlex when a key is present). A
   result claimed as "complete" needs at least two independent indexes that
   actually answered.
3. **Dedupe on ANY stable identifier — a DOI is not required.** arXiv ids,
   DBLP keys and ACL-Anthology ids are all citable. DOI-less ML-proceedings
   papers (ICLR/ICML/NeurIPS) and modern EDBT must NOT be discarded for
   lacking a Crossref DOI. The union merges twins across identifier types
   (a Crossref DOI record and its arXiv-id twin collapse to one) by stable id,
   then by normalized title+year.
4. **Distinguish "no verifiable identifier → drop" from "provider down →
   retry/fallback."** A clean `0 results` from a healthy provider is real;
   a `ProviderError` is not a "0 results." Re-query an unresolved candidate on
   the other indexes; if it still can't be confirmed, flag it
   `unresolved-keep` rather than dropping it on a single-index miss.
5. **Emit a per-run provider-coverage report and stamp COMPLETE vs PARTIAL.**
   The run is `PARTIAL` whenever any authoritative index was degraded or
   unreachable (or fewer than two answered), so a degraded run is visibly
   flagged and never reported as exhaustive. `polite_http.note_provider` /
   `provider_report` / `coverage_status` keep the in-process ledger.

Single-provider scripts keep their old fatal behavior (a direct
`dblp_search.py` run still exits nonzero on a hard failure via
`http_get`) — only the orchestrated flow fails over. This is a copilot, not an
autopilot: it never fabricates a hit to fill a gap, never promises acceptance,
and flags arXiv-only hits as preprints.

## Citation-graph expansion (`citation_graph.py`)

Keyword/venue search saturates and *structurally* misses three classes of
paper one citation edge away — foundational/seminal anchors the sub-area is
built on, direct competitors that share citers but not query keywords, and
shared-infrastructure deps every paper cites but none names in a topic query.
They are reachable only by following edges, which is why this is the single
largest recall lever. `citation_graph.py` does it key-free:

- **OpenAlex** (`api.openalex.org`, CC0): both edge directions plus influence.
  `referenced_works` (refs-of) + `?filter=cites:<WID>` (cited-by) +
  `cited_by_count`; resolve seeds by `doi:`/`<WID>`/`arxiv:`/`title.search:`;
  batch-resolve neighbor ids via `?filter=ids.openalex:a|b|c` (≤50/req). One
  polite page per call; `meta.count` gives true totals without crawling.
- **Crossref** references-of fallback: the work's `reference` array carries
  DOIs (`GET /works/<doi>`, no `select` on the single-work route) — keeps the
  anchor/infra sweep working key-free even if OpenAlex ever gates the
  cited-by filter (Crossref has no first-class cites filter, so that direction
  degrades, not the refs direction).

Re-rank neighbors by **co-citation degree** (how many seeds touch each), run a
per-cluster foundational-anchor sweep (`--direction refs`, sort by global
citations), and a claim-driven niche pass (mine the brief's distinctive
mechanism noun-phrases into narrow queries, feed hits back as seeds). Full
method: `references/citation-graph-expansion.md`. Neighbors are recall
*candidates*: confirm venue/acceptance before presenting them and route
citations through `verify-citations`.

## Canonical-instance resolution (version drift & title collisions)

Every provider ranks a title query by *relevance*, which answers "does a paper
with this title exist?" — not "is this the instance the community cites?" Two
recurring traps follow, and both pass a bare existence check:

- **Version / edition drift**: a title has a known successor (V2/V3, `++`,
  `2.0`, a trailing roman numeral, "revised/extended/revisited", or a
  year-reissue) and the search returns the *older* edition. The newer
  canonical version often has *fewer* citations (less time to accrue), so
  ranking by citations alone picks the wrong one.
- **Same-author title collision**: two papers share a first-author surname and
  a near-duplicate title stem (a workshop paper vs. its journal extension; a
  short vs. long version; an adjacent follow-up). The relevance winner may be
  the lower-impact or non-seminal one.

`scripts/resolve_canonical.py` post-processes the candidate list (the `--json`
of any search script — it fetches nothing) and applies three GENERIC,
domain-agnostic heuristics; it hardcodes no venue, author, or paper:

1. **prefer-latest-canonical** — if any cluster member carries an explicit
   version marker (regex over general version tokens + edition words), the
   newest such version is PREFERRED and older siblings are flagged.
2. **title-collision clustering** — records are grouped when their title stems
   (content words, stop-worded, version-stripped, order-independent) collide
   *and* they share a first-author surname. The shared-author guard lets the
   stem-overlap bar relax (Jaccard 0.45, or ≥2 distinctive shared words) so
   genuine near-duplicates surface without over-merging unrelated same-author
   work (distinct topics stay separate).
3. **de-duplication by impact** — within an ambiguous cluster, rank by impact
   signal (`citationCount` / `is-referenced-by-count`), then earliest year as
   a seminal-venue proxy when impact is tied or absent (e.g. DBLP records,
   which carry no citation counts).

It is a **copilot**: every ambiguous cluster prints `PREFERRED` + `sibling`
lines and a one-line `CHOOSE:` note, never auto-collapsing to one. The picked
instance still goes through `verify-citations` before any bibliography. The
heuristics are tunable in one place (the vocab/threshold constants at the top
of the script) without touching the search scripts.

## Politeness and licensing rails

Baked into `scripts/polite_http.py` — do not work around them:

1. ≤1 request/second per host (2s DBLP, 3s arXiv), persisted across
   invocations in `.cache/find-papers/_ratelimit.json`.
2. Identifying User-Agent `research-paper-skills (mailto:$CONTACT_EMAIL)`;
   Crossref also gets `mailto=`.
3. Exponential backoff on HTTP 429 (and on connection resets), honoring
   `Retry-After`; clean nonzero exit after 4 attempts.
4. 24h response cache under `.cache/find-papers/` (gitignored). Use
   `--no-cache` only when you genuinely need fresher data.
5. Single-page fetches only: no cursor crawling, no continuation tokens, no
   bulk dumps. Refine the query instead of paging.
6. Metadata (DOIs, titles, authors, venues, counts) is safe to keep and
   commit. Abstracts and full text are fetch-on-demand, display-transiently:
   never write them into the repo or its outputs.

## Adjacent providers

- **Unpaywall** (`api.unpaywall.org/v2/<doi>?email=...`): DOI → legal OA PDF;
  needs a real email (example.com → HTTP 422). Used by the `fetch-paper`
  skill; 100k calls/day.
- **OpenAlex**: CC0 data, but key-required + credit-metered since Feb 2026;
  ACM proceedings venue mapping is unreliable (`primary_location.source`
  often null) — enumerate via DBLP instead, enrich by DOI if you have a key.
- **IEEE Xplore / CORE**: key + approval gated; poor fit for a key-free
  skill. IEEE metadata flows through Crossref anyway.
