---
name: draft-related-work
description: Drafts or rewrites a Related Work / prior work section positioned against actually-retrieved papers — clusters prior work into themes, articulates the delta (what this paper adds) per cluster, follows the target community's placement and citation conventions (numeric ACM/IEEE vs natbib author-year, single- vs double-blind self-citation, where the section sits at NeurIPS/CHI/SIGMOD-style venues), and admits only verified citations. Use when the user says "related work", "prior work", "position my paper against the literature", "how do we differ from X", "reviewers said related work is thin/missing/a laundry list", or asks to add citations to a draft. Works from papers found via find-papers and/or an existing .bib — it never invents references.
---

# Draft Related Work

Produces a Related Work section that *positions* the paper — every paragraph
is a cluster of actually-retrieved prior work plus an explicit delta sentence —
formatted to the target venue's conventions. This is a writing skill with a
hard anti-hallucination gate: a citation that was not retrieved and verified
in this session does not ship.

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

- The paper's core claim/contributions (from the draft's intro, or ask).
- Target venue — a `venues/conferences/<id>.yml` profile if one exists.
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

2. **Assemble the candidate pool — retrieved papers only.** Sources:
   the user's `.bib`, `find-papers` results, references/citations of the 1–2
   closest known papers (`find-papers --paper` style lookups). Target 10–25
   candidates. A paper enters the pool only with a concrete identifier (DOI
   or arXiv ID). If the user names a paper without one, find it first; if it
   cannot be found, say so — never proceed on a guessed reference.

3. **Build the clustering worksheet.** Run:

   ```
   python3 scripts/gather_candidates.py <DOI> <arXiv-ID> ... [--from-file ids.txt]
   ```

   It fetches each paper's metadata one polite request at a time (title,
   year, venue, citation count, abstract, tldr) and prints a worksheet with
   empty `cluster:` / `delta:` slots. Treat the output as transient working
   material — it contains abstracts; never commit it. Identifiers it flags
   as unresolved (exit 3) are unverified: park them until cleared. Where the
   abstract is missing or the paper is pivotal, read it via `fetch-paper`.

4. **Cluster and articulate the delta per cluster.** Group the pool into
   3–6 themes along the axis that makes *this* paper's gap visible, then
   write one delta sentence per cluster: what the cluster achieves, what it
   lacks for this paper's problem, what this paper does about it. Method,
   patterns, and anti-patterns:
   [references/clustering-and-deltas.md](references/clustering-and-deltas.md).
   Show the user the cluster plan (cluster names, members, delta sentences)
   before writing prose — restructuring is cheap now, expensive later.

5. **Draft the section.** One paragraph per cluster (claim sentence →
   representative works → limitation → delta), a dedicated paragraph for the
   single closest competitor, and a closing positioning paragraph. Match the
   venue: citation commands and self-citation voice per step 1, length per
   the family norm (typically 0.5–1 page at conference venues). Emit `.tex`
   (or markdown if the draft is not LaTeX) plus BibTeX entries for any
   citation not already in the user's `.bib` — entries built strictly from
   retrieved metadata. Add a comparison table only when the criteria in the
   clustering reference are met.

6. **Audit deterministically.** Run:

   ```
   python3 scripts/audit_bib.py refs.bib --tex related-work.tex
   ```

   Fix every blocking finding: cite keys missing from the `.bib`, duplicate
   entries, entries with no DOI/eprint/URL (unverifiable — the classic
   hallucinated-reference shape), incomplete entries. The style census in
   its output must match the venue's convention.

7. **Gate through `verify-citations`.** Every entry cited by the new section
   gets verified against Crossref/DBLP/S2 before delivery. Anything that
   fails verification is removed from the prose or explicitly flagged to the
   user as unconfirmed — never left in silently, and never "fixed" by
   inventing plausible fields.

## Output

- The drafted/rewritten Related Work section (`.tex` or markdown), clustered,
  with a delta per cluster, in the venue's citation style.
- New BibTeX entries (metadata only — always safe to keep).
- A short positioning summary: clusters, per-cluster delta, the closest
  competitor and the precise distinction, plus anything left unverified.

## Guardrails

- Never fabricate, embellish, or "reconstruct from memory" a citation; every
  reference must trace to a retrieval in this session and pass
  `verify-citations`. A thin-but-true section beats a padded one.
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
  — clustering axes, the per-cluster paragraph pattern, delta phrasing,
  comparison tables, anti-patterns, handling the closest competitor.
- [references/placement-conventions.md](references/placement-conventions.md)
  — per-community placement and length norms, citation-command styles,
  blind-level self-citation rules, how to verify conventions empirically.
