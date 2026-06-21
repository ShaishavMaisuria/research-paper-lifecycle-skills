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
7. [Politeness and licensing rails](#politeness-and-licensing-rails)
8. [Adjacent providers (when the big four are not enough)](#adjacent-providers)

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

Notes: ACM has NO public API — DBLP/Crossref carry its metadata, and since
Jan 1 2026 the whole ACM DL is open access (`dl.acm.org/doi/pdf/<doi>`,
single fetches only; bulk crawling stays banned by ACM ToU). OpenAlex
requires an API key since Feb 2026, so it is out of this skill's key-free
default path (profiles still record `openalex_source` ids for users who
bring a key).

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
