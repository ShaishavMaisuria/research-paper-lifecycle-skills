# Search methodology for literature reviews

## Contents

- [Query design](#query-design)
- [Venue enumeration (the alias problem)](#venue-enumeration-the-alias-problem)
- [Snowballing](#snowballing)
- [Stopping criteria](#stopping-criteria)
- [Screening protocol](#screening-protocol)
- [Forward-reference reconciliation](#forward-reference-reconciliation)
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

### Seed from multiple, topically-diverse seeds — not one convenient paper

The single biggest snowballing failure is seeding from one convenient paper.
Its neighborhood is dominated by *that paper's* sub-area, so the harvested
set drifts to adjacent-but-uncited siblings and silently misses the parts of
the topic the one seed does not touch.

Rule: pick **one seed per theme/sub-problem of the question** (so ≥3 seeds for
a 3–6-theme review), and make them topically diverse:

- spread the seeds across the question's axes (e.g. the method axis, the
  task/application axis, the evaluation axis), not three papers from the same
  cluster;
- include the most-cited / most-central paper in each sub-area, so each
  neighborhood is anchored on that sub-area's seminal work, not a peripheral
  one;
- if the question explicitly names a sub-area you have no seed for, that is a
  gap — find a seed for it before snowballing, or the corpus cannot cover it.

Then expand each seed (one call per paper, not bulk):

- **Backward**: fetch the paper's reference list with find-papers'
  single-paper lookup and nested fields (verified working pattern):
  `s2_search.py --paper DOI:<doi> --fields title,references.title,references.externalIds,references.year --json`
  then screen titles that match the criteria.
- **Forward**: same lookup with
  `--fields title,citations.title,citations.externalIds,citations.year` —
  catches work newer than the seed.

### Inclusion gate: role in THIS paper's argument

A harvested neighbor enters the corpus only if you can name its **role in the
question's argument**. Tag each adopted paper with one role:

- `method-we-extend` — the work the review (or the user's paper) builds on;
- `baseline` — something compared against, or that this line of work beats;
- `eval-task` — defines a dataset/benchmark/metric the area is measured on;
- `foundational-lineage` — the backbone / seminal ancestor the methods inherit.

If a neighbor fits none of these roles for *this* question, it is an
adjacent-but-uncited sibling — exclude it with that reason. This keeps the
neighborhood from drifting into a different sub-area.

### Co-citation sanity check

After snowballing, sanity-check that you landed in the topic's real
neighborhood, not a sibling one: take the question's seminal papers (the
high-citation anchors) and confirm the adopted set has **non-trivial overlap**
with their reference/citation lists. Near-zero overlap is a red flag that the
seeds were off-area — re-seed before screening rather than shipping a corpus
that misses the topic's core lineage. Record the check (which anchors, rough
overlap) in the review's method section.

One round of snowballing per seed is usually enough. Import any adopted hits
through `corpus.py import --source snowball` so provenance is recorded, and set
the role with `corpus.py set KEY --reason "role: baseline"` (or a `theme`/note
tag) so the inclusion rationale is auditable.

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

## Forward-reference reconciliation

A draft or related-work plan names methods, baselines, and backbones in prose
as slots to fill — "we extend X", "compared against Y and Z", "built on the W
backbone". A recurring failure is that those named works are parked and the
corpus ships without them: the prose leans on a name that no verified
reference backs, silently breaking the citation chain. Worse, the missing ones
are usually the *load-bearing* references — the very methods and baselines the
argument stands on.

Close the loop **after the draft/plan exists and before declaring the corpus
complete**:

1. Run the reconciliation gate over the draft (and the plan, if separate):

   ```
   python3 scripts/forward_refs.py review.md [plan.md] --corpus <ws>/corpus.json
   ```

   It extracts method/baseline/backbone-shaped names (acronyms, CamelCase
   system names, hyphenated model names, and explicit `<SLOT>` markers),
   diffs them against the corpus keys and included-paper titles, and emits the
   unresolved ones as a **retrieval worklist**.

2. Treat the worklist as mandatory work, not advice. For each genuine missing
   work, loop it back through the full pipeline — `find-papers` search →
   screen → `fetch-paper` → extract → `verify-citations` — exactly like any
   other paper. Never hand-add it straight to the references.

3. The extractor is heuristic (a copilot, not an oracle): some entries will be
   the user's own system, a dataset, or a metric, not a citable work. Dismiss
   those deliberately; do not let them push you to invent a citation.

4. Re-run until the worklist is empty of real references, then the corpus is
   complete. The gate is warn-only by default; use `--strict` (exit 1 on any
   unresolved name) when wiring it into a pre-finalization check.

## The search log

`corpus.py import --query "..."` appends to `search_log` in `corpus.json`
automatically (date, source, query, hits added). For the review's method
section, summarize: providers used, query variants, date of search, counts
at each stage (found → screened → included). This is the difference between
"some papers I found" and a review someone can trust or reproduce.
