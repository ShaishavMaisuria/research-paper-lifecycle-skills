---
name: draft-survey
description: Turns a topic into a ranked reading list of the best papers plus a two-column, arXiv-ready literature-review/survey draft grounded in verified citations. Use when a researcher says "write a survey on X", "do a literature review of X", "give me a ranked reading list on X", "what should I read on X first", "draft a survey paper for arXiv", or "two-column related-work survey on X". Searches across DBLP/Crossref/Semantic Scholar/arXiv, ranks candidates by citation impact, venue strength, recency, and citation-graph centrality, clusters them into a taxonomy, verifies every reference, and writes an original-prose survey (intro, taxonomy, per-theme synthesis, open problems) where each claim cites a real, resolved paper. Never fabricates citations, never copies source text — original synthesis only; the author stays the author. Trigger words - survey, literature review, reading list, ranked papers, what to read, arxiv survey, two-column review.
---

# Draft Survey

Two deliverables from one topic: a **ranked reading list** (what to read, best first, with a one-line why) and a **two-column, arXiv-ready survey draft** that synthesizes the area in original prose with verified citations. Composes [`find-papers`](../find-papers/SKILL.md), [`verify-citations`](../verify-citations/SKILL.md), [`study-exemplars`](../study-exemplars/SKILL.md), and [`draft-related-work`](../draft-related-work/SKILL.md).

## When to use vs. literature-review

- [`literature-review`](../literature-review/SKILL.md) builds the *related-work for your own paper* — scoped to your contribution.
- `draft-survey` produces a **standalone survey/review document** (a reading list + a publishable 2-column draft) of a whole area. Use it to learn a field fast or to draft a survey paper for arXiv.

## Inputs

- The **topic** (e.g. "geospatial data conflation"), optionally a sub-scope and a target length (default 5–6 two-column pages).
- Optional: a venue/format (default: generic two-column `article`, which compiles on arXiv).

## Process

1. **Gather candidates broadly.** Run `find-papers` across DBLP + Crossref + Semantic Scholar + arXiv for the topic and its synonyms; then run its **citation-graph expansion** so seminal anchors and direct lineages are not missed (a survey that omits the foundational papers is a weak survey).
2. **Rank them.** Run `python3 scripts/rank_papers.py candidates.json` — a composite of normalized citation count, venue tier, recency, and citation-graph centrality (weights documented in [references/ranking-criteria.md](references/ranking-criteria.md)). Output the **ranked reading list**: rank, title, authors, year, venue, a citation/impact signal, and a one-line *why read this* (seminal / survey / SOTA / dataset / contrarian). Keep seminal and recent both represented.
3. **Verify every entry.** Route the list through `verify-citations` so each has a real DOI/arXiv id; drop or flag anything unresolved. A survey with a fabricated reference is disqualifying.
4. **Build a taxonomy.** Cluster the verified papers into 3–6 themes/sub-problems (the survey's section structure), each with its lineage (foundational → recent).
5. **Draft the survey, in original prose.** Write a two-column `.tex`: abstract, introduction (scope + why a survey now), one section per theme (synthesize and contrast methods — never copy source sentences), a cross-cutting comparison (a table helps), open problems / future directions, conclusion, and `\bibliography`. Every claim cites a verified paper. Target the requested length.
6. **Make it arXiv-ready.** Ensure it compiles (`latexmk`), uses a portable two-column class, and the `.bib` is clean. arXiv has no peer-review desk-reject, but it expects a compilable source and a real abstract; `preflight-check` can sanity-check length/structure.

## Output

- `reading-list.md` — the ranked, verified, annotated reading list.
- `survey.tex` + `refs.bib` — the two-column, arXiv-ready draft (original prose, verified citations).
- Both written to `paper-workspace/research/` or a path the user names.

## Guardrails

- **Real citations only.** Every reference is resolved via `verify-citations`; never invent a paper, DOI, author, or year to fill a gap.
- **Original synthesis, not copying.** Summarize and contrast in your own words; do not paste sentences from abstracts or papers. No paper content is bundled (fetch on demand, process transiently).
- **No completeness theater.** State the search scope and that a survey is never exhaustive; flag themes where coverage is thin rather than padding.
- Copilot, not pilot: the author reviews the reading list and the draft, and is the author of any submission.

## Source verification

Citation impact and venue facts come from live scholarly APIs, not memory, and each cited paper carries a resolvable identifier the user can open.

## Memory

Uses `.paper-memory/` as described by [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md): read prior reading lists/lessons for the topic at start; append the topic, the chosen taxonomy, and any coverage gaps at end (deduped).
