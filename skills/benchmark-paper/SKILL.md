---
name: benchmark-paper
description: Scores a draft against the measurable patterns of recent award-winning and top-cited papers at a target venue, producing a shareable venue-fit scorecard. Use when a researcher asks "score my paper", "how does my paper compare to best papers at SIGSPATIAL/NeurIPS/...", "is my paper good enough for this venue", "benchmark my draft against award winners", "rate my paper out of 10", or wants a readiness scorecard before submitting. Builds an exemplar corpus via study-exemplars, extracts comparable structural and rhetorical features from the draft, and reports a per-dimension scorecard plus an overall venue-fit index — explicitly a conformance measure (does the draft match the form of strong work at this venue), never a prediction of acceptance, award, or scientific quality. Trigger words - score my paper, rate my paper, benchmark, scorecard, compare to best papers, award winners, venue fit, am I ready to submit.
---

# Benchmark Paper

Produces a **venue-fit scorecard**: how closely a draft matches the measurable patterns of recent award-winning and top-cited papers at the target venue. This is a *conformance* gauge to help an author find gaps before submitting — it is **not** a prediction of acceptance, a best-paper forecast, or a judgment of scientific merit.

Pairs naturally with [`simulate-reviewers`](../simulate-reviewers/SKILL.md) (which red-teams content quality) and [`study-exemplars`](../study-exemplars/SKILL.md) (which it calls to build the comparison corpus). Run `preflight-check` first — a desk-reject defect makes any score moot.

## When to use

- The author wants a single, shareable readiness signal before submitting.
- The author asks how their draft stacks up against the venue's strongest recent papers.
- The author wants to know *which dimensions* are weakest relative to exemplars, ranked by fixability.

## When NOT to use it (say this plainly to the user)

- It cannot judge whether the science is novel, correct, or important — the things that actually win awards. Use `simulate-reviewers` for content critique.
- It cannot predict acceptance or a best-paper award. Anyone who claims a tool can is selling false precision.
- A high score on a flawed paper is meaningless. Conformance to form ≠ quality of substance.

## Inputs

- The draft: a `.tex` file (or compiled PDF / markdown), with `.bib` if available.
- The target venue id (e.g. `sigspatial-2026`) → its profile in `venues/`.
- Optional: a corpus size N (default 8 exemplars) and a recency window (default last 5 years).

## Process

1. **Resolve the venue profile** from `venues/conferences/<venue>.yml`. If missing, ask the user or have `add-venue-profile` create it. Re-verify the venue is correct before scoring.
2. **Build the exemplar corpus.** Invoke `study-exemplars` to fetch (on demand, legally, transiently) N recent best-paper awardees and top-cited papers at the venue, and extract their feature profile. **Never** bundle or store paper text. If award lists are unavailable, fall back to top-cited and say so in the report — the corpus basis must be disclosed.
3. **Extract the draft's comparable features** along the dimensions in [references/scoring-rubric.md](references/scoring-rubric.md) (section architecture, contribution framing, evaluation rigor signals, claim/citation density, abstract structure, figure/table conventions, reproducibility artifacts). Use `verify-citations` output if present so the citation-integrity dimension is grounded.
4. **Score each dimension** as conformance to the exemplar distribution, with an explicit basis for every number (what was measured, what the exemplar range was). Run `python3 scripts/scorecard.py features.json --venue <id>` to compute and render deterministically — do not eyeball the aggregate.
5. **Report**: the scorecard (per-dimension 0–10 + venue-fit index), the 3 weakest dimensions ranked by fixability, concrete fixes tied to exemplar patterns, and the mandatory caveat block. Offer the one-line shareable summary the user can screenshot.

## Output

A `scorecard.md` containing:
- **Venue-fit index** (0–10) with a one-line plain-English band (e.g. "structurally in line with recent {venue} winners; evaluation section is the gap").
- **Per-dimension table**: score, exemplar range, your value, basis.
- **Top fixes** ranked by impact × ease.
- **Corpus disclosure**: which papers formed the basis, award-vs-cited, recency.
- **Caveats** (always): conformance not quality; not an acceptance/award prediction; human judgment required.

## Guardrails

- Every score states what was measured and the exemplar range it was compared against. No bare numbers.
- Never present the index as a probability of acceptance or an award. Refuse to, if asked — explain why.
- Corpus is fetched on demand from open-access sources, processed transiently, never stored or committed (see `study-exemplars`).
- Never fabricate exemplar data to fill the corpus; if you can't reach N papers, score against fewer and disclose it.
- This is a copilot signal, not a verdict. The author decides.

## Memory

Uses the shared `.paper-memory/` convention in the user's paper directory (full spec: [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `.paper-memory/profile.yml` (vertical, venue tier) to pick exemplar emphasis, and `lessons.md` to recall which dimensions were weak last run and any `recurring` gaps for this author — lead with them.
- **At end:** append durable findings in the shared format `- [YYYY-MM-DD] (benchmark-paper | <scope>) weak-dimension -> recommendation` (via `reflect-and-improve`'s `reflect_log.py append`, which dedupes and dates). A dimension that lags exemplars across drafts is `recurring`; a one-time gap is `this-paper`. Do not log the full scorecard, only the lasting takeaways.
- Create `.paper-memory/` on demand if absent and offer to add it to the project `.gitignore`. It is local-only; never upload it or copy it into this repo.
