# Venue ranking sources — where prestige numbers actually come from

How to look up, interpret, and safely cite CORE rank, h5-index, acceptance
rates, CCF class, and deadline data. None of these have a stable key-free API,
so most lookups are manual or web-search driven — this file tells you exactly
where to look and what each number does and does not mean.

## Table of contents

- [Golden rules](#golden-rules)
- [CORE rank (conferences)](#core-rank-conferences)
- [Google Scholar Metrics h5-index](#google-scholar-metrics-h5-index)
- [Acceptance rates](#acceptance-rates)
- [CCF catalogue (China Computer Federation)](#ccf-catalogue-china-computer-federation)
- [Journal-side signals](#journal-side-signals)
- [Deadline aggregators](#deadline-aggregators)
- [Indicative CORE ranks for the profiled venues](#indicative-core-ranks-for-the-profiled-venues)
- [Venue identity across databases (the alias problem)](#venue-identity-across-databases-the-alias-problem)
- [Citing rankings in papers, CVs, and grant text](#citing-rankings-in-papers-cvs-and-grant-text)

## Golden rules

1. **Never state a rank, h5-index, or acceptance rate from memory as fact.**
   Either look it up live and record the source + retrieval date, or label it
   "indicative — verify" in the output.
2. **Every number is edition-stamped.** CORE has editions (CORE2023, ...);
   Scholar Metrics refreshes yearly; acceptance rates differ per track per
   year. A naked number without an edition/year is meaningless.
3. **Prestige is one signal of four.** Topic fit and track fit beat rank: a
   perfectly fitting CORE-A venue usually serves the paper better than a
   poorly fitting A* venue. See `track-fit.md` for the scoring rubric.

## CORE rank (conferences)

- **What**: Australia's Computing Research and Education association ranks CS
  conferences A* (flagship, top ~4%), A, B, C, plus unranked/national tiers.
  The de-facto standard prestige label in CS outside China.
- **Where**: <https://portal.core.edu.au/conf-ranks/> — search by acronym or
  title. No official API; the portal has a search UI and exportable result
  pages. Cite the edition shown in the result row (e.g. "CORE2023").
- **How to look up**: web-search `site:portal.core.edu.au <acronym>` or open
  the portal search directly. Match on acronym AND full title — acronym
  collisions are common (e.g. "GIS" vs unrelated venues).
- **Caveats**: editions lag reality by 1-3 years; workshops and new venues are
  unranked (not the same as bad); journals are NOT covered (CORE's journal
  ranking (ERA-derived) is frozen/historical — use other signals for journals).

## Google Scholar Metrics h5-index

- **What**: h5-index = the largest number h such that h articles published in
  the last 5 complete years have at least h citations each. Captures venue
  citation volume; favors large venues.
- **Where**: <https://scholar.google.com/citations?view_op=top_venues> —
  browse by category/subcategory (e.g. Engineering & Computer Science →
  Data Mining & Analysis), or search the venue name in the Metrics search
  box. No API; lookup is manual or via web search
  `google scholar metrics h5-index <venue name>`.
- **Interpretation in CS (rough 2026 bands)**: flagship ML venues run very
  high (NeurIPS/ICLR/CVPR are in the hundreds); strong specialized SIG
  conferences commonly sit in the 40-90 band; healthy niche venues 20-40.
  Compare venues **within the same subfield only** — h5 across subfields
  mostly measures community size.
- **Caveats**: arXiv categories appear in the lists and dwarf real venues;
  venue-name ambiguity (Scholar merges/splits venues unpredictably); biased
  toward older, larger, English-language venues.

## Acceptance rates

- **What**: accepted / submitted for a given track and year. Researchers
  over-weight this; it varies wildly year-to-year and track-to-track.
- **Primary sources (most reliable first)**:
  1. The venue's own "message from the PC chairs" / preface in the
     proceedings front matter (fetch via DOI from the proceedings).
  2. The conference website's news/statistics page or opening-slides deck.
  3. Community aggregations — e.g. the GitHub repo
    `lixin4ever/Conference-Acceptance-Rate` (ML/NLP/CV focused) and
    per-community pages (csrankings-adjacent wikis). Treat as secondary;
    spot-check against a primary source before citing.
- **Caveats**: never average across tracks (research vs short vs demo differ
  by 2-4x); "acceptance rate" sometimes excludes desk rejects; venues with
  rolling/journal-style review (PVLDB, PACMMOD) publish per-cycle numbers.
  If you cannot source a number, write "not published / unknown" — do not
  estimate.

## CCF catalogue (China Computer Federation)

- **What**: CCF classifies international venues A/B/C per subfield. The
  decisive ranking for researchers at Chinese institutions (promotion and
  graduation requirements reference CCF class directly).
- **Where**: official catalogue at <https://www.ccf.org.cn/Academic_Evaluation/By_category/>
  (Chinese); the deadline tracker ccfddl (below) embeds each venue's CCF
  class in its YAML — the easiest machine-readable mirror.
- **When to use**: ask the user whether CCF class matters to them (it does
  for most users at Chinese institutions); if yes, report CCF class alongside
  CORE in the shortlist.

## Journal-side signals

For journal targets (TKDE, TODS, ...): use Scholar Metrics h5-index,
Scimago SJR quartiles (<https://www.scimagojr.com/>), and CCF class. Impact
factor is paywalled (Clarivate) — do not guess it. Journals have no
acceptance-rate culture; review latency (first-decision time, often stated on
the journal's author-guidelines page) is the number researchers actually need.

## Deadline aggregators

The repo's `venues/conferences/*.yml` profiles are the first stop (run
`scripts/list_venues.py`). For venues not yet profiled:

- **ccfddl** — <https://ccfddl.com>, data at GitHub `ccfddl/ccf-deadlines`
  (machine-readable YAML per venue incl. CCF class). Broadest CS coverage.
- **aideadlin.es** — ML/AI venues.
- **sec-deadlines.github.io** — security/privacy venues.
- **WikiCFP** — <http://www.wikicfp.com> — long-tail venues and workshops;
  noisy, verify everything.

Aggregators track **dates only** — never page limits, blind level, or
formats. And dates on aggregators go stale: always confirm against the
venue's own CFP page before the user plans around a date.

## Indicative CORE ranks for the profiled venues

Snapshot for orientation only (CORE2023 era). **Verify at
<https://portal.core.edu.au/conf-ranks/> before putting any of these in a
deliverable** — editions change and this table does not update itself.

| Venue (profile id) | Indicative CORE | Note |
|---|---|---|
| neurips-2026, icml-2026, iclr-2026 | A* | flagship ML |
| cvpr-2026 | A* | flagship vision |
| kdd-2026 | A* | flagship data mining |
| sigmod-2026, vldb-2026, icde-2026 | A* | flagship data management |
| aaai-2026 | A* | flagship AI |
| www-2026 | A* | flagship web |
| chi-2026 | A* | flagship HCI |
| sigspatial-2026 | A | top spatial venue |
| edbt-2026 | A | strong data management |
| icdm-2026 | A* | data mining (rank moved between editions — verify) |
| tkde, tods | n/a | journals — CORE conference ranking does not apply |

## Venue identity across databases (the alias problem)

The same venue has different identifiers everywhere: DBLP key `conf/gis`,
Semantic Scholar venue string `SIGSPATIAL/GIS`, Crossref container titles
that change phrasing yearly, and often no OpenAlex source at all (verified
for SIGSPATIAL). Profiles store the resolved set under `aliases:`. For a
venue with no profile, resolve its canonical identity first:

```
CONTACT_EMAIL=you@example.org python3 scripts/dblp_venue_lookup.py search "<venue name>"
```

DBLP (CC0, key-free) is the authoritative registry of CS venues; the
returned `dblp_key` is what a future profile stores as `aliases.dblp_key`.
`toc-count <key> <year>` gives the venue's yearly paper count — a useful
size/health proxy when h5-index is ambiguous (a venue publishing 30
papers/year and one publishing 500 are different beasts at equal "rank").

## Citing rankings in papers, CVs, and grant text

If the user will put a rank into a document (grant, CV, thesis intro):
verify it live the same day, and cite source + edition + retrieval date,
e.g. "CORE2023 rank A* (portal.core.edu.au, retrieved 2026-06-11)". If the
claim needs a bibliographic citation, route it through the
`verify-citations` skill like any other reference — never fabricate one.
