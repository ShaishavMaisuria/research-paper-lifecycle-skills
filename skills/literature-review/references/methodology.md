# Search methodology for literature reviews

## Contents

- [Query design](#query-design)
- [Venue enumeration (the alias problem)](#venue-enumeration-the-alias-problem)
- [Snowballing](#snowballing)
- [Stopping criteria](#stopping-criteria)
- [Screening protocol](#screening-protocol)
- [The search log](#the-search-log)

## Query design

Derive 3–5 query variants from the research question before searching:

1. **Canonical phrase** — the term of art ("learned index", "spatial join").
2. **Synonym variants** — older or competing names ("ML-enhanced index",
   "instance-optimized"). Ask the user which community terms apply.
3. **Decomposed query** — problem term + technique term separately, for
   providers with weak phrase search (DBLP matches on title words).

Run each variant against at least two providers (different providers index
different things):

| Provider | Script (find-papers skill) | Best for |
|---|---|---|
| DBLP | `dblp_search.py --query "..."` | CS titles, exact venue enumeration, CC0 |
| Crossref | `crossref_search.py` | DOI metadata, journals, citation counts |
| Semantic Scholar | `s2_search.py` | Relevance ranking, abstracts, TLDRs, citation graph |
| arXiv | `arxiv_search.py` | Preprints, latest work not yet in proceedings |

Use `--json` and pipe the hits into the corpus:

```
python3 ../find-papers/scripts/dblp_search.py --query "learned spatial index" --json > hits.json
python3 scripts/corpus.py --corpus <ws>/corpus.json import hits.json --source dblp --query "learned spatial index"
```

Cap each query at ~30 hits. If a query returns hundreds, narrow it (year
range, venue, extra term) rather than importing noise.

## Venue enumeration (the alias problem)

When the scope says "papers from venue V", enumerate the venue's proceedings
instead of keyword-searching. Each API names the same venue differently —
this repo ships the mapping in `venues/conferences/<id>.yml` under `aliases`:

- `aliases.dblp_key` → `dblp_search.py --key conf/gis --year 2025`
  (toc query; returns the complete proceedings, e.g. 195 SIGSPATIAL 2025
  papers)
- `aliases.s2_venue` → S2 venue string (e.g. `SIGSPATIAL/GIS`) for
  `s2_search.py` venue filters
- `aliases.crossref_container` → Crossref `query.container-title` string

If no profile exists for the venue, discover the DBLP key first:
`dblp_search.py --find-venue NAME`, and consider contributing a profile.

Venue profiles are starting points, never ground truth. If any profile fact
becomes load-bearing for the review (track structure, what counts as the main
proceedings vs workshops), re-verify against the live `cfp_url` listed in the
profile before relying on it.

Note: DBLP toc queries for some venues return workshop papers too (Crossref
container-title queries almost always do). Filter by checking the `venue` /
container string on each hit during screening.

## Snowballing

After the keyword/venue pass, expand from the 2–3 most central included
papers (one call per paper, not bulk):

- **Backward**: fetch the paper's reference list via
  `s2_search.py` (S2 `/paper/{id}/references`) and screen titles that match
  the criteria.
- **Forward**: fetch citing papers via S2 `/paper/{id}/citations` — catches
  work newer than the seed.

One round of snowballing is usually enough. Import any adopted hits through
`corpus.py import --source snowball` so provenance is recorded.

## Stopping criteria

Stop searching when ANY of:

1. The last query variant returned no new relevant titles (saturation).
2. Forward+backward snowballing of central papers yields only already-seen
   work.
3. The included set reached the agreed target size — report saturation
   status honestly rather than padding.

Record which criterion fired in the review's Scope and Method section.

## Screening protocol

A lightweight PRISMA-style pass, tracked entirely in `corpus.json`:

1. **Criteria first.** Write 2–4 inclusion and 2–4 exclusion criteria into
   `corpus.json` (`criteria`) before screening anything. Typical axes: topic
   match, year range, venue class (peer-reviewed vs preprint), paper type
   (technique vs survey vs demo).
2. **Title/venue pass.** Exclude obvious misses. Every exclusion gets a
   reason: `corpus.py set KEY --screened excluded --reason "..."`.
3. **Abstract pass.** For survivors, fetch the abstract on demand
   (`s2_search.py` by DOI). Decide included/excluded. Abstracts are read
   transiently — never pasted into notes, the corpus, or the review.
4. **User checkpoint.** Show `corpus.py stats` plus the included list with
   one-line reasons. Get explicit approval before fetching full texts —
   full-text reading is the expensive phase.

Excluded papers stay in the corpus with their reasons: that audit trail is
what makes the review defensible (and `check_review.py` will fail any
citation of an excluded paper).

## The search log

`corpus.py import --query "..."` appends to `search_log` in `corpus.json`
automatically (date, source, query, hits added). For the review's method
section, summarize: providers used, query variants, date of search, counts
at each stage (found → screened → included). This is the difference between
"some papers I found" and a review someone can trust or reproduce.
