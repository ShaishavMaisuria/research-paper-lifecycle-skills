---
name: draft-related-work
description: Drafts or rewrites a Related Work / prior work section positioned against actually-retrieved papers — derives the REQUIRED clusters from the paper's own claimed scope (not just whatever was retrieved), clusters prior work into themes, articulates the delta (what this paper adds) per cluster, enforces a per-cluster citation floor and routes empty expected clusters back to find-papers, follows the target community's placement and citation conventions (numeric ACM/IEEE vs natbib author-year, single- vs double-blind self-citation, where the section sits at NeurIPS/CHI/SIGMOD-style venues), and admits only verified citations. Use when the user says "related work", "prior work", "position my paper against the literature", "how do we differ from X", "reviewers said related work is thin/missing/a laundry list", or asks to add citations to a draft. Works from papers found via find-papers and/or an existing .bib — it never invents references.
---

# Draft Related Work

Produces a Related Work section that *positions* the paper — every paragraph
is a cluster of actually-retrieved prior work plus an explicit delta sentence —
formatted to the target venue's conventions. This is a writing skill with two
hard gates:

- **Anti-hallucination.** A citation that was not retrieved and verified in
  this session does not ship.
- **Anti-structural-hole.** The clusters the section MUST cover are derived
  from the paper's *own claimed scope*, never from whatever `find-papers`
  happened to return. A retrieved-but-peripheral corpus produces an outline
  that positions confidently while leaving a hole exactly where the paper
  lives — a missing direct-competitor cluster, an absent canonical lineage, a
  whole expected sub-area with zero citations. That gap is found
  deterministically and routed back to `find-papers` as a targeted second
  pass, not shipped as a silent author to-do.

## When to use

- Drafting Related Work for a new paper, given a topic and a target venue.
- Rewriting an existing section reviewers called a "laundry list", "thin",
  "missing comparisons", or "unclear novelty".
- Folding newly found papers (or a reviewer's "you missed X, Y, Z") into an
  existing section without breaking its structure.
- NOT for finding papers (use `find-papers`), reading one paper
  (`fetch-paper`), a full thematic survey (`literature-review`), or checking
  an existing bibliography only (`verify-citations`).

## Inputs

- The paper's core claim/contributions, AND its sub-tasks/requirements (from
  the draft's intro/abstract, or ask). These drive the required-cluster
  enumeration in step 2 — without them the section can only mirror the
  retrieved pile.
- Target venue — a `venues/conferences/<id>.yml` profile if one exists
  (its `exemplar_distribution` calibrates the section's length/breadth).
- Candidate prior work: output of `find-papers` / `literature-review`, the
  draft's `.bib`, and/or papers the user names.
- `CONTACT_EMAIL` env var for the metadata script (prompts if unset).

## Process

1. **Pin down the venue's conventions.** Read `venues/conferences/<id>.yml`
   (fields: `family`, `format.template`, `review.blind`, track page limits)
   and the family file it references. Profiles are a starting point, never
   ground truth — re-verify anything that affects the draft (template, blind
   level, page budget) against the live `cfp_url` before relying on it.
   Then read [references/placement-conventions.md](references/placement-conventions.md)
   for where the section goes, how long it runs, citation-command style, and
   self-citation rules at that venue family. When conventions are unclear,
   confirm empirically: pull 3–5 recent papers from the venue itself
   (`find-papers` DBLP toc query, `study-exemplars`) and observe placement.

2. **Derive the REQUIRED clusters from the paper's claimed scope — before
   looking at what was retrieved.** Enumerate the paper's contributions,
   sub-tasks, and requirements from the brief/intro. For each, name the
   cluster of *direct prior approaches* a reviewer would expect to see
   positioned against, plus the foundational-lineage / canonical anchor that
   sub-area is built on (the originating method, not only the latest
   refinement). This list is the *target*; it does not yet have citations.
   Driving it from claimed scope (not the corpus) is what makes it generalize
   across papers and venues, and is what surfaces the hole the retrieved pile
   hides. Method and worked examples:
   [references/clustering-and-deltas.md](references/clustering-and-deltas.md)
   (§ Required clusters from claimed scope).

3. **Assemble the candidate pool — retrieved papers only.** Sources:
   the user's `.bib`, `find-papers` results, the references and citations of
   the 1–2 closest known papers (`find-papers --paper` style lookups). Pull
   deliberately *toward the required clusters from step 2*, not just whatever
   a topic search returned. Target 10–25 candidates. A paper enters the pool
   only with a concrete identifier (DOI or arXiv ID). If the user names a
   paper without one, find it first; if it cannot be found, say so — never
   proceed on a guessed reference.

4. **Build the clustering worksheet.** Run:

   ```
   python3 scripts/gather_candidates.py <DOI> <arXiv-ID> ... [--from-file ids.txt]
   ```

   It fetches each paper's metadata one polite request at a time (title,
   year, venue, citation count, abstract, tldr) and prints a worksheet with
   empty `cluster:` / `delta:` slots. Treat the output as transient working
   material — it contains abstracts; never commit it. Identifiers it flags
   as unresolved (exit 3) are unverified: park them until cleared. Where the
   abstract is missing or the paper is pivotal, read it via `fetch-paper`.

5. **Map the pool onto the required clusters and run the coverage gate.**
   Assign each retrieved paper to one of the step-2 required clusters (a
   paper that fits none is an outlier — keep only if reviewer-expected).
   Write the assignment into a small plan file (one block per required
   cluster, listing the cite keys assigned). **Tag each key by evidence tier**
   so precision stays visible and the floor cannot be met by padding — append
   `!graph` / `!keyword` / `!heuristic` to a key the paper is *not confirmed*
   to cite (an untagged key means "the paper is known to cite this"):

   ```
   "refs": ["li2018deep", "yao2019computing",          # confirmed-cited
            "smith2023!graph",   # surfaced by citation-graph edge — plausible
            "doe2022!heuristic"] # 'a strong paper would cite this' — weakest
   ```

   Then run:

   ```
   python3 scripts/check_coverage.py plan.json   # or plan.txt (see --help)
   ```

   Only **confirmed-cited** refs count toward the floor. The gate FAILs
   (exit 3) on any required cluster with **zero confirmed cites** — including
   one "covered" only by speculative refs (padding masks a real hole) — and
   WARNs below the floor (default 2). It also prints a **precision estimate**
   (confirmed / total) and caps heuristic-only additions (default 2 across the
   plan, `--heuristic-cap`) so the core set stays scope-justified. On a failing
   or thin cluster, take its emitted **second-pass retrieval worklist** back
   to `find-papers` and fill the gap with *confirmed* cites, then re-run — do
   NOT draft over an empty required cluster, satisfy the floor by padding with
   speculative refs, or ship a gap as a silent author to-do. Only when the gate
   clears (or the user explicitly accepts a documented thin cluster) proceed to
   clustering prose.

6. **Cluster and articulate the delta per cluster.** With coverage cleared,
   group the pool into 3–6 themes along the axis that makes *this* paper's
   gap visible, then write one delta sentence per cluster: what the cluster
   achieves, what it lacks for this paper's problem, what this paper does
   about it. Method, patterns, and anti-patterns:
   [references/clustering-and-deltas.md](references/clustering-and-deltas.md).
   Show the user the cluster plan (cluster names, members, delta sentences)
   before writing prose — restructuring is cheap now, expensive later.

7. **Draft the section.** One paragraph per cluster (claim sentence →
   representative works → limitation → delta), a dedicated paragraph for the
   single closest competitor, and a closing positioning paragraph. Match the
   venue: citation commands and self-citation voice per step 1; **calibrate
   length and breadth to the venue family's measured exemplar median**, not
   to maximal coverage — read the profile's `exemplar_distribution`
   (`related_work` band when present) or measure 3–5 recent venue papers via
   `study-exemplars`, falling back to the family norm in
   [references/placement-conventions.md](references/placement-conventions.md)
   only when neither exists. Emit `.tex` (or markdown if the draft is not
   LaTeX) plus BibTeX entries for any citation not already in the user's
   `.bib` — entries built strictly from retrieved metadata. Add a comparison
   table only when the criteria in the clustering reference are met.

8. **Audit deterministically.** Run:

   ```
   python3 scripts/audit_bib.py refs.bib --tex related-work.tex
   ```

   Fix every blocking finding: cite keys missing from the `.bib`, duplicate
   entries, entries with no DOI/eprint/URL (unverifiable — the classic
   hallucinated-reference shape), incomplete entries. The style census in
   its output must match the venue's convention.

9. **Gate through `verify-citations`.** Every entry cited by the new section
   gets verified against Crossref/DBLP/S2 before delivery. Anything that
   fails verification is removed from the prose or explicitly flagged to the
   user as unconfirmed — never left in silently, and never "fixed" by
   inventing plausible fields.

## Output

- The drafted/rewritten Related Work section (`.tex` or markdown), clustered,
  with a delta per cluster, in the venue's citation style.
- New BibTeX entries (metadata only — always safe to keep).
- A short positioning summary: the required clusters derived from scope and
  whether each cleared the coverage gate, per-cluster delta, the closest
  competitor and the precise distinction, plus anything left unverified.
- The coverage gate's **precision estimate** (confirmed-cited / total refs)
  and any **speculative additions** (graph/keyword/heuristic tier) called out
  explicitly as plausible-but-unconfirmed, so the user can prune them before
  submission rather than treating cluster-floor satisfaction as proof of
  citation. When the ground truth is a known subset, report recall against
  that subset separately from this precision band.
- If any required cluster could not be filled, the second-pass retrieval
  worklist (for `find-papers`) reported explicitly — never buried as a silent
  author to-do.

## Guardrails

- Never fabricate, embellish, or "reconstruct from memory" a citation; every
  reference must trace to a retrieval in this session and pass
  `verify-citations`. A thin-but-true section beats a padded one.
- The required clusters come from the paper's claimed scope, never from the
  retrieved corpus alone — positioning only against what happened to be
  returned leaves a hole where the paper actually lives. A required cluster
  with zero citations is a blocking gap routed back to `find-papers`, never a
  silent author to-do, and never papered over by stretching an adjacent
  cluster to cover it.
- This is a copilot, not an autopilot: the coverage gate, the second-pass
  worklist, and any decision to accept a documented thin cluster are surfaced
  to the user — the skill does not silently decide a gap is acceptable.
- Calibrate length and breadth to the venue family's measured exemplar median,
  not maximal coverage; over-citing to look thorough reads as survey drift.
- Precision is a first-class quality signal, not just recall. A reference the
  paper is not confirmed to cite (a citation-graph neighbor, a keyword hit, or
  a "a strong paper would cite this" hunch) is a *hypothesis*, not a hit: tag
  it by tier, never promote it to the same status as a confirmed cite, and cap
  hunch-only additions. Adjacent/foundational clusters get ranked by
  load-bearing necessity and trimmed to the floor plus the few most-cited
  canonical members — defer the rest to an optional pool rather than padding a
  section beyond what the paper actually carries.
- Never misstate what a cited paper does to inflate the delta — strawman
  characterizations are the fastest way to a hostile reviewer (who is often
  the cited author).
- Abstracts and paper text are processed transiently and never committed;
  worksheet output stays out of the repo.
- Respect the scripts' politeness rails: identifiers one at a time, ≤25 per
  run, no bulk harvesting.
- Venue profiles can be stale — critical facts get re-verified against the
  live CFP. Never submit anything on the user's behalf.

## References

- [references/clustering-and-deltas.md](references/clustering-and-deltas.md)
  — deriving required clusters from claimed scope, the citation floor and
  zero-citation gap routing, clustering axes, the per-cluster paragraph
  pattern, delta phrasing, comparison tables, anti-patterns, handling the
  closest competitor.
- [references/placement-conventions.md](references/placement-conventions.md)
  — per-community placement and length norms, calibrating length to the
  venue's measured exemplar median, citation-command styles, blind-level
  self-citation rules, how to verify conventions empirically.

## Scripts

- `scripts/gather_candidates.py` — fetch metadata for retrieved identifiers
  into a transient clustering worksheet (polite, one paper at a time).
- `scripts/check_coverage.py` — deterministic coverage gate: FAIL on any
  required cluster with zero *confirmed-cited* citations (including one padded
  only with speculative refs), WARN below the citation floor, report a
  precision estimate (confirmed/total) and a per-plan heuristic-tier cap, and
  emit a targeted second-pass retrieval worklist for `find-papers`. Cite keys
  carry an optional evidence-tier marker (`key!graph` / `!keyword` /
  `!heuristic`); only confirmed (untagged) keys count toward the floor.
- `scripts/audit_bib.py` — offline citation/bib audit and style census.
