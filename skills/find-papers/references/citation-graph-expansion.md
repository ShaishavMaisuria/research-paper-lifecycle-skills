# Citation-Graph Expansion: the recall stage keyword search can't reach

Topic/keyword search **saturates**: past the first page or two it keeps
returning the same on-topic hits and stops adding new ones. What it
*systematically* misses is not on the same topic *in words* — it is one
citation edge away:

1. **Foundational / seminal anchors** — the base model, dataset, or theorem
   the whole sub-area is built on. A paper rarely re-states its own
   foundations in language that matches a topic query.
2. **Direct competitors** — methods solving the same problem that share
   *citers* with your seeds but were branded with different keywords, so a
   keyword query never co-locates them.
3. **Shared-infrastructure dependencies** — the toolkit/benchmark/library
   every paper in the field cites but none *names* in a topic query (the
   feature extractor, the SLAM front-end, the RL baseline, the eval harness).

These three are reached by **edges, not words**. `citation_graph.py`
implements the expansion; this doc is the method behind it and the manual
fallback when you'd rather drive the APIs by hand.

## Table of contents

1. [When to run it](#when-to-run-it)
2. [The two edge directions](#the-two-edge-directions)
3. [The expansion recipe](#the-expansion-recipe)
4. [Co-citation re-ranking (why degree beats relevance)](#co-citation-re-ranking)
5. [Foundational/seminal anchor sweep](#foundational-anchor-sweep)
6. [Cover the niche, not just the canon (claim-driven pass)](#cover-the-niche)
7. [Provider endpoints (key-free)](#provider-endpoints)
8. [Honesty and guardrails](#honesty-and-guardrails)

## When to run it

Run the expansion **after the keyword/venue seed pass saturates** — i.e. when
a fresh keyword query mostly returns papers you already have, or when the
brief implies foundations/competitors/infra you haven't surfaced yet. It is a
recall booster layered on top of keyword search, never a replacement: you need
a handful (2-8) of genuinely on-topic seeds first. Garbage seeds in, garbage
neighbors out.

This is the single largest lever on recall in literature reconstruction. If
you only do keyword search, you will reliably miss the base model a method
fine-tunes, the competitor sharing its reviewers, and the library in its
every experiment.

## The two edge directions

| Direction | OpenAlex | What it surfaces |
|---|---|---|
| **references-of** (seed → what it cites) | `referenced_works` field on the work | anchors + shared infrastructure deps |
| **cited-by** (seed ← what cites it) | `GET /works?filter=cites:<WID>` | direct competitors + newer follow-on work |

`refs` pulls the field's *substrate* (older, high global-citation anchors and
the infra every paper leans on). `citedby` pulls the field's *frontier*
(competitors and successors). Run **both** unless you specifically want only
foundations (`--direction refs`) or only the frontier (`--direction citedby`).

## The expansion recipe

`citation_graph.py` does all of this; the steps are spelled out so you can
audit or reproduce them by hand.

1. **Resolve each seed to a canonical work id.** Prefer DOI; fall back to an
   OpenAlex/arXiv id; last resort `filter=title.search:<title>` (title search
   is fuzzy — eyeball that it resolved to the *right* paper).
2. **Pull both edge sets per seed.** references-of from `referenced_works`;
   cited-by from `filter=cites:<WID>` (one polite page, no crawling — capped
   at 50 citers/seed by default, which is plenty to find the hubs).
3. **Tally co-citation degree.** Count how many *distinct seeds* touch each
   neighbor. A neighbor that 4 of your 6 seeds cite is almost certainly an
   anchor or shared dep, even if its title shares zero query keywords.
4. **Re-rank by `(seed_degree, global_citations)`.** Cross-seed hubs first;
   among equal-degree neighbors, the globally most-cited (the likely
   foundational anchors) rise. Raise `--min-degree 2+` to keep *only* hubs
   shared across seeds.
5. **Batch-resolve titles/years/DOIs** for the survivors in one call
   (`filter=ids.openalex:a|b|c`, ≤25 ids/request) and present as candidates.

## Co-citation re-ranking

Relevance ranking (what keyword APIs give you) scores a paper by how well its
*text* matches your *query*. That is exactly the signal that fails for
anchors, competitors, and infra. **Co-citation degree** scores a paper by how
many of your seeds *cite or are cited by* it — a structural signal that is
blind to wording. The two are complementary: keyword search seeds the graph,
the graph finds what keyword search structurally cannot. Always present the
seed-degree alongside each neighbor so the human can see *why* it surfaced.

## Foundational anchor sweep

Per topical cluster (run this once the seed set for a cluster stabilizes):

1. `--direction refs` on the cluster's seeds.
2. Sort survivors by **global citations descending** — the script already
   tie-breaks on this, but eyeball the top of the `refs` list specifically.
3. The highest global-citation, highest seed-degree `refs` neighbors are the
   sub-area's anchors (base models, canonical datasets, the founding method).
   Add them as explicit candidates even if no keyword query would return them.
4. Sanity check coverage: does every cluster have its obvious foundation
   present? A diffusion cluster with no DDPM/U-Net, a fine-tuning cluster with
   no base model, an SfM cluster with no bundle-adjustment anchor = a recall
   hole the sweep should close.

## Cover the niche

The anchor sweep covers the *canon*. It will still miss the niche-specific
competitor that is neither foundational nor widely cited — so add a
**claim-driven pass** that mines the brief for its distinctive mechanism
noun-phrases and turns each into a targeted query (generic technique; no
fixed vocabulary):

1. Read the brief/abstract and extract the **distinctive mechanism
   noun-phrases** — the specific named technique, component, loss, operator,
   or data construct that makes this work *this* work (not the generic topic
   words). The test: would a competitor doing the same thing have to name this
   concept too?
2. For each noun-phrase, run a *narrow* targeted query (S2 `--query`, arXiv
   `abs:"<phrase>"`, Crossref `--query`) — narrower than your topic query, so
   it surfaces the few papers sharing that exact mechanism rather than the
   broad topic crowd.
3. Feed any new on-topic hits back in as **additional seeds** and re-run the
   graph expansion. One mechanism-matched competitor often pulls in the rest
   of the niche through shared citers.

Anchor sweep (refs, by global citations) + cited-by frontier + claim-driven
mechanism queries together cover canon, competitors, and niche — the three
holes the keyword pass leaves.

## Provider endpoints

All verified key-free in the polite `mailto` pool (2026-06). Politeness,
caching, and 429 backoff come from `polite_http.py` automatically.

**OpenAlex** (`api.openalex.org`, CC0):
- `GET /works/doi:<doi>` / `/works/<WID>` / `/works/arxiv:<id>` — resolve a
  seed; `select=referenced_works,cited_by_count` gives one edge direction +
  influence in the same call.
- `GET /works?filter=cites:<WID>` — the cited-by direction; `meta.count` is
  the true total even when you read one page.
- `GET /works?filter=ids.openalex:a|b|c` — batch-resolve up to ~50 neighbor
  ids per request (the script uses 25).
- `GET /works?filter=title.search:<title>` — title→work fallback for
  DOI-less seeds (fuzzy; verify the match).

**Crossref** (`api.crossref.org`, facts): references-of fallback only — the
work's `reference` array carries DOIs (`GET /works/<doi>`, no `select` on the
single-work route). Use when a seed has a DOI but OpenAlex didn't resolve it.

> Note: OpenAlex still answers without a key in the polite pool as of
> 2026-06; if a future credit/key requirement bites, the Crossref
> references-of path keeps the foundational/infra sweep working key-free
> (the cited-by direction degrades — Crossref has no first-class cites
> filter).

## Honesty and guardrails

- A graph neighbor is a **candidate, never a result**. The script labels them
  so. Confirm venue/acceptance via DBLP/Crossref before presenting any as a
  published paper, and route anything entering a bibliography through
  `verify-citations`. Never say "I found N papers" about raw neighbors.
- You are a copilot, not a pilot: surface high-degree neighbors with the
  *reason* they surfaced (seed-degree, edges) and let the human decide what's
  in scope. Do not silently auto-include.
- No fabrication: every neighbor comes from an actual OpenAlex/Crossref
  response in this session. If a provider fails, say so; do not fill the gap
  from memory.
- Respect the rate limits and single-page rule — the graph fans out fast;
  cap citers per seed (default 50) and seeds per run (2-8) rather than
  crawling whole citation neighborhoods.
