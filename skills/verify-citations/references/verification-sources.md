# Verification sources — providers, authority, aliasing, retractions

## Table of contents

1. [Authority order: which index settles a dispute](#authority-order)
2. [Crossref](#crossref)
3. [DBLP](#dblp)
4. [arXiv](#arxiv)
5. [Semantic Scholar](#semantic-scholar)
6. [DataCite](#datacite)
7. [Retraction data](#retraction-data)
8. [The venue-alias problem](#the-venue-alias-problem)
9. [Fetching canonical BibTeX](#fetching-canonical-bibtex)
10. [Rate limits, keys, and politeness](#rate-limits-keys-and-politeness)
11. [Licensing and copyright](#licensing-and-copyright)

## Authority order

When sources disagree about an entry, trust in this order:

1. **The DOI registry record** (Crossref, or DataCite for datasets/Zenodo/
   arXiv-issued DOIs) — deposited by the publisher; authoritative for title,
   author list, year, and container (venue) of the *published version*.
2. **DBLP** — human-curated, authoritative for CS venue names, author name
   disambiguation, and "which conference did this really appear at".
3. **arXiv** — authoritative for preprints only. An arXiv record's year is
   the *preprint* year; if the entry cites the published version, the venue
   record wins on year and venue.
4. **Semantic Scholar** — aggregated; useful as a tie-breaker and for
   coverage outside CS, but it inherits upstream errors. Never the sole basis
   for declaring a .bib entry wrong.

## Crossref

- DOI lookup: `https://api.crossref.org/works/{urlencoded-doi}` — 404 means
  the DOI does not exist in Crossref (try DataCite before declaring it fake).
- Bibliographic search: `https://api.crossref.org/works?query.bibliographic=
  {title}&rows=5&select=DOI,title,author,issued,container-title`.
- No key needed. Append `mailto={CONTACT_EMAIL}` for the polite pool. 429 on
  excess; the bundled script backs off exponentially.
- Caveats: `author` is occasionally missing or family/given-swapped for some
  publishers; `issued` may be the online-first year (off by one from the
  print year a .bib cites); proceedings `container-title` is the long form
  ("Proceedings of the 31st ACM International Conference on ...").

## DBLP

- Search API: `https://dblp.org/search/publ/api?q={query}&format=json&h=10`.
  CC0-licensed metadata, no key. Informal rate limit — keep ~1 req/s, bursts
  get 429.
- Best title-resolution source for CS papers without a DOI. Hits include
  title, authors (with disambiguation suffixes like "Wei Wang 0001" — the
  script strips these), year, venue key, DOI, and electronic edition URL.
- DBLP records the *published* venue for conference papers, which is exactly
  what you want when an entry has both an arXiv ID and a `booktitle`.
- No abstracts, no citation counts — by design; it is a bibliography, and
  that is what makes it trustworthy for this skill.

## arXiv

- ID lookup: `https://export.arxiv.org/api/query?id_list={id}&max_results=1`
  (Atom XML). No key. Etiquette: 3 seconds between calls — the script
  enforces this per host.
- ID shapes: new-style `2104.12345` (optional `vN`), old-style
  `cs.DB/0123456`. DOIs of the form `10.48550/arXiv.XXXX` are DataCite DOIs
  arXiv mints — resolve them via the arXiv API, not Crossref.
- A nonexistent ID returns an error entry / empty feed → ARXIV_NOT_FOUND.
- Year caveat: arXiv `published` is the v1 submission date. A .bib entry
  citing the conference version legitimately has a later year (the script
  tolerates up to +3 years in that direction).

## Semantic Scholar

- Title match: `https://api.semanticscholar.org/graph/v1/paper/search/match?
  query={title}&fields=title,year,authors,externalIds,venue` — returns the
  single best match or HTTP 404 when nothing matches (404 here means "no such
  paper", not an error).
- Anonymous access shares a global pool and 429s frequently; a free key
  (semanticscholar.org/product/api) gives a dedicated 1 req/s. The script
  sends it from `S2_API_KEY` when set.
- S2 venue strings are short canonical forms (e.g. `SIGSPATIAL/GIS`,
  `NeurIPS`) — see [the venue-alias problem](#the-venue-alias-problem).
- **Citation counts & multiple instances** (canonical-instance check): the
  `/paper/search` endpoint with `fields=...,citationCount,publicationTypes`
  returns several same-titled records with their citation counts and artifact
  types. The script uses this to surface, e.g., a far-more-cited conference
  paper when an entry resolves to a less-cited RFC/report of the same work.
  Counts are facts S2 reports — fine to show the user; never invent one.
- **Reference lists for co-citation** (relevance gate): Crossref
  `works/{doi}?select=reference` returns a work's outgoing reference DOIs. The
  relevance gate intersects each entry against the union of the confirmed core
  set's references to estimate co-citation density. Read-only metadata.
- License: ODC-BY. Fine to fetch and compare; do not redistribute bulk data
  or store fetched abstracts in the repo.

## DataCite

- DOI lookup: `https://api.datacite.org/dois/{doi}` — covers Zenodo,
  figshare, arXiv-minted DOIs, datasets, software. A DOI absent from
  Crossref but present in DataCite is real (commonly software/data
  citations). Absent from both → DOI_NOT_FOUND.

## Retraction data

Three complementary signals (the script checks the first two automatically):

1. **Crossref editorial updates**: works that update a DOI are findable via
   `https://api.crossref.org/works?filter=updates:{doi}` — each hit's
   `update-to` lists the target DOI and a type: `retraction`, `withdrawal`,
   `removal`, `partial_retraction` (→ ERROR), `expression_of_concern`
   (→ WARN), `correction`/`erratum` (→ INFO). Crossref incorporated the
   Retraction Watch database (2023), so coverage is good but not total —
   notices only exist where a publisher or Retraction Watch deposited them.
2. **Title markers**: many publishers (Springer Nature, Elsevier) rename the
   article itself to "RETRACTED ARTICLE: ..." or "WITHDRAWN: ...".
3. **OpenAlex `is_retracted`** (manual fallback): `https://api.openalex.org/
   works/doi:{doi}` exposes a boolean `is_retracted`. OpenAlex requires a
   free API key for sustained use (since Feb 2026); keyless singleton lookups
   still work for spot checks. Use this when the user wants a second opinion
   on a specific suspicious DOI.

Always tell the user that retraction checking is best-effort: a clean result
means "no notice found", not "not retracted".

## The venue-alias problem

The same venue carries different names in every index — the single biggest
source of false VENUE_MISMATCH flags. Verified example, one conference:

| Index | SIGSPATIAL appears as |
|---|---|
| DBLP | venue key `conf/gis` (e.g. `db/conf/gis/gis2025`) |
| Semantic Scholar | `SIGSPATIAL/GIS` |
| Crossref | `Proceedings of the 31st ACM International Conference on Advances in Geographic Information Systems` |
| A typical .bib | `SIGSPATIAL '23` or `Proc. ACM SIGSPATIAL` |

All four are the same venue. Therefore:

- VENUE_MISMATCH is a **warning**, never an automatic error. Confirm by eye
  before telling the user their venue is wrong.
- The repo's `venues/conferences/*.yml` profiles carry an `aliases:` block
  (`dblp_key`, `s2_venue`, `crossref_container`) — consult the matching
  profile to recognize aliases for covered venues. Profiles are starting
  points: if you rely on any venue fact beyond aliases (names change across
  years), re-verify against the live `cfp_url` listed in the profile.
- Abbreviation styles (`Proc. VLDB Endow.` vs `Proceedings of the VLDB
  Endowment`) are both correct; consistency within one .bib is a style
  matter for the venue's reference format, not a verification failure.

## Fetching canonical BibTeX

When an entry needs fixing, fetch the record — never retype from memory:

- **DBLP** (best for CS; clean, venue-correct BibTeX):
  `curl -s "https://dblp.org/rec/{dblp-key}.bib"` — the script prints the
  DBLP record URL on resolution; append `.bib` to it.
- **doi.org content negotiation** (works for any Crossref/DataCite DOI):
  `curl -sL -H "Accept: application/x-bibtex" "https://doi.org/{doi}"`
- Preserve the original citation key when replacing an entry so `\cite`
  commands keep working; diff old vs new and show the user.
- Publisher-negotiated BibTeX sometimes uses month/page formats the venue
  style dislikes — tidy formatting freely, but never alter title, authors,
  year, venue, or DOI away from the canonical record.

## Rate limits, keys, and politeness

| Host | Limit applied by script | Key |
|---|---|---|
| api.crossref.org | 1 req/s + mailto polite pool | none |
| dblp.org | 1 req/s | none |
| export.arxiv.org | 1 req / 3 s | none |
| api.semanticscholar.org | 1 req/s + backoff | optional `S2_API_KEY` |
| api.datacite.org | 1 req/s | none |

The script also: sends `User-Agent: research-paper-skills
(mailto:$CONTACT_EMAIL)` everywhere, retries HTTP 429 with exponential
backoff honoring `Retry-After`, caches every response for 24 h under
`.cache/verify-citations/` (gitignored), and fetches one item at a time —
never bulk. Do not bypass any of this; it is what keeps the user's IP off
blocklists.

## Licensing and copyright

- Bibliographic **metadata is safe everywhere**: Crossref treats it as facts,
  DBLP is CC0, DataCite metadata is open.
- **Abstracts and full text are not metadata.** Do not store them in the repo
  or in reports; this skill never needs them.
- Semantic Scholar data is ODC-BY (attribution; no bulk redistribution).
- Retraction-notice DOIs and statuses are facts — fine to record in reports.
