# Finding Exemplars — sources, verification, selection

How to assemble a defensible exemplar set: where award lists actually
live, how to verify them, how to pick top-cited papers without falling
for citation-count artifacts, and how to resolve open-access copies.

## Table of contents

1. [Award sources](#1-award-sources)
2. [Award verification protocol (mandatory)](#2-award-verification-protocol-mandatory)
3. [Top-cited methodology and caveats](#3-top-cited-methodology-and-caveats)
4. [Composing the final set](#4-composing-the-final-set)
5. [Open-access resolution order](#5-open-access-resolution-order)
6. [Venue-alias gotchas](#6-venue-alias-gotchas)
7. [Politeness and copyright contract](#7-politeness-and-copyright-contract)

## 1. Award sources

Best-paper awards live on **web pages, not APIs**. Check, in order:

1. **The venue's own awards page.** Patterns that usually work:
   - Year site: `<year-site>/awards`, `/program/awards`, or a news post
     announcing winners during/after the conference
   - SIG/steering-committee page: e.g. sigspatial.org, sigmod.org,
     sigchi.org keep cumulative best-paper lists across years
   - The venue profile's `website` field is the entry point; for older
     years, swap the year in the site URL or search
     `site:<domain> "best paper"`
2. **Aggregators** (convenient, but secondary sources — verify):
   - jeffhuang.com/best_paper_awards — long-running aggregate of
     best-paper awards across ~30 CS conferences
   - Wikipedia pages of major conferences sometimes list awards
3. **OpenReview venue pages** (NeurIPS/ICML/ICLR) tag award/oral/spotlight
   decisions on the paper's forum page — primary source for ML venues.
4. **Test-of-time / 10-year-impact awards** — often a *better* exemplar
   signal than best-paper (the community's verdict after a decade), but
   note the paper was written to decade-old conventions; weight its
   *framing* lessons, not its formatting.

Distinguish award tiers when reporting: best paper, best paper runner-up /
honorable mention, best student paper, best short/demo/poster paper,
test-of-time. Match the tier to the user's track.

## 2. Award verification protocol (mandatory)

Awards are the easiest thing in this skill to hallucinate. Apply both
checks to every candidate; drop (or explicitly mark unverified) anything
failing either:

1. **Live source URL** — the award claim must come from a page actually
   fetched in this session (venue/SIG page, year-site news, OpenReview
   forum, or an aggregator). Record the URL next to the claim. "I recall
   that paper X won" is never sufficient.
2. **DBLP metadata match** — confirm the paper exists with the claimed
   venue and year:

   ```bash
   python3 scripts/lookup_exemplar.py --title "Exact Title From The Award Page"
   ```

   The script flags exact-normalized title matches and prints venue, year,
   DOI. A title on an award page that has no DBLP record for that
   venue-year is a red flag (typo'd aggregator, renamed camera-ready, or a
   fabricated memory) — resolve the discrepancy before using the paper.

When the venue page and an aggregator disagree, the venue page wins.
Cite the source URL for every award claim in the final brief.

## 3. Top-cited methodology and caveats

One polite request ranks a venue-year window:

```bash
python3 scripts/rank_top_cited.py --venue "SIGSPATIAL/GIS" --year 2020-2023 --top 10
python3 scripts/rank_top_cited.py --venue-profile venues/conferences/sigspatial-2026.yml \
    --year 2020-2023 --top 10 --json
```

The script calls Semantic Scholar's bulk venue search (verified pattern:
`venue=SIGSPATIAL/GIS&year=2025` → 191 papers), sorts by `citationCount`,
and prints DOIs plus OA hints. Selection caveats:

- **Recency bias.** Citations accumulate over years. Never rank the
  current or previous proceedings year and call it "top"; use a window
  ending 2–3 years back (for a 2026 study: 2020–2023 is sound). The
  script warns when the window touches the last two years.
- **Genre inflation.** Surveys, benchmarks, and datasets out-cite
  technical papers. They are fine exemplars *if* the user is writing one;
  otherwise prefer the top-cited *research* papers (check
  `publicationTypes` and the title).
- **Influential citations.** The script also prints S2's
  `influentialCitationCount`; a high influential/total ratio signals
  methodological influence rather than drive-by citation.
- **Cross-check the venue string.** If the total looks wrong (a major
  venue returning 12 papers), the S2 venue string is probably off —
  compare against a DBLP toc count for the same year (`find-papers`
  skill, `dblp_search.py --key <dblp_key> --year <year>`). Totals within
  ~10–20% of each other mean the alias is right (S2 and DBLP disagree
  slightly on workshop/companion inclusion).
- Counts are a **snapshot** — date-stamp them in the brief and attribute
  Semantic Scholar (ODC-BY).

## 4. Composing the final set

- 5–8 papers: 3–4 verified awardees + 3–4 top-cited, overlapping is fine
  (an awarded paper that is also top-cited is the strongest exemplar)
- Spread across 3–4 proceedings years so one year's PC taste doesn't
  masquerade as the venue convention
- Match the user's track and length: study full research papers to write
  one; study awarded demos/short papers for a 4-page submission — the
  conventions differ completely
- Confirm the roster with the user before fetching full texts; fetching
  is the slow, rate-limited part

## 5. Open-access resolution order

Fetch one paper at a time, transiently. Resolution order:

1. `openAccessPdf` URL from the ranking/lookup script output (S2's own OA
   resolution; verify the license at the source)
2. The `fetch-paper` skill (`python3 skills/fetch-paper/scripts/resolve_oa.py
   <DOI> --json`) — Unpaywall `best_oa_location`, arXiv PDF/HTML, ACM-OA
   fallback, with download support
3. arXiv directly when an arXiv ID is known: `arxiv.org/html/<id>`
   (easiest to read), else `arxiv.org/pdf/<id>` — preprint caveat applies
4. ACM venues (DOI prefix `10.1145/`): the ACM Digital Library is fully
   open access since Jan 1, 2026 — `https://dl.acm.org/doi/pdf/<doi>`.
   dl.acm.org **blocks scripted downloads**: give the user the URL to
   open in a browser; never spoof or retry around the block.
5. No legal copy → skip the paper, list it in the brief as
   "not analyzed (no open copy)". Never use shadow libraries, never
   bypass paywalls, never ask the user to upload a paywalled PDF "to be
   safe" (they may, on their own initiative, share a copy they have
   lawful access to — still process it transiently).

Note the **version** analyzed (`publishedVersion` / `acceptedVersion` /
`submittedVersion`). Structure analysis of a preprint can differ from the
camera-ready (page limits, missing acknowledgments, different appendices).

## 6. Venue-alias gotchas

The same venue has different names in every API. Resolution order:

1. `venues/conferences/<id>.yml` → `aliases:` block (`s2_venue` for the
   ranking script, `dblp_key` for cross-checks)
2. The `find-papers` skill's `references/venue-aliases.md` (~20 top
   venues with per-venue gotchas)
3. Live discovery via DBLP venue search, then record what you learned

High-frequency traps: SIGSPATIAL is `SIGSPATIAL/GIS` on S2 and `conf/gis`
on DBLP; WWW is "The Web Conference" on S2; VLDB papers live in
`journals/pvldb` by *volume*, not conference year; post-2023 SIGMOD
papers are published as PACMMOD. A wrong S2 venue string returns 0 papers
silently — the ranking script exits 3 with a hint instead of reporting an
empty venue as fact.

## 7. Politeness and copyright contract

- Scripts enforce: ≤1 request/s per host (2 s for DBLP), User-Agent
  `research-paper-skills (mailto:$CONTACT_EMAIL)`, exponential backoff on
  HTTP 429, 24 h response cache under `.cache/study-exemplars/`
  (gitignored). Do not loop scripts to paginate, do not bulk-harvest a
  proceedings, do not strip the contact email.
- `CONTACT_EMAIL` must be a real address (Unpaywall rejects placeholders
  with HTTP 422; Crossref/DBLP use it to contact rather than block).
- Metadata (DOI, title, authors, counts) may be kept and committed. This
  includes the **measured exemplar bundle** — the aggregated
  `exemplar_distribution:` block (density bands, rates, modal section names,
  `n`, `recency`, `as_of` date) built by `build_exemplar_bundle.py` and
  cached into a venue/family profile (rubric §14). Bands and counts are not
  copyrightable expression; caching them is what lets a downstream fallback
  rest on real measured exemplars instead of a hand-written family
  description when a live fetch fails.
- Paper text, abstracts, figures: fetch on demand, process transiently,
  never store, never commit, never redistribute. The full rule set lives
  at the top of [analysis-rubric.md](analysis-rubric.md).
