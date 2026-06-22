# How the reading list is ranked

`rank_papers.py` scores each candidate on a transparent composite (all factors normalized 0–1 across the candidate pool), so the ranking is explainable, not a black box.

| Factor | Weight | What it captures | Source |
|---|---|---|---|
| Impact | 0.45 | log-scaled citation count — surfaces seminal work without letting one mega-cited paper dominate linearly | Semantic Scholar / Crossref `citation_count` |
| Centrality | 0.25 | how many papers *in the candidate set* cite it — in-area importance, robust to field-size differences in raw citations | citation-graph (`find-papers` expansion) |
| Recency | 0.20 | newer papers up-weighted so the state of the art isn't buried under old classics | `year` |
| Venue | 0.10 | a light bump for strong venues; deliberately small so a strong paper at a minor venue still ranks | venue string |
| Survey bonus | 0.05 | ensures at least one orienting survey/review lands near the top | title / type |

## Why these weights

- **Impact + centrality together (0.70)** dominate, because a survey reader most needs the papers the field actually builds on. Citation count alone over-rewards age; centrality within the set corrects for that and for cross-field citation-rate differences.
- **Recency (0.20)** is meaningful but not dominant — a survey must cover both the foundational lineage and the current frontier. The reading list is meant to show both; `draft-survey` keeps seminal and recent represented even if pure score would crowd one out.
- **Venue (0.10)** is intentionally light: venue is a weak proxy for quality and over-weighting it entrenches prestige bias.

## Honesty rules

- Ranking ranks *what it's given* — it can only be as good as the candidate pool, so run a broad multi-API search + citation-graph expansion first.
- Citation counts are a popularity signal, not a quality guarantee; the one-line "why" labels (seminal / recent / central / survey) tell the reader what kind of paper each is so they judge for themselves.
- All counts come from live scholarly APIs, never from memory, and should be reported with source/provider metadata.
