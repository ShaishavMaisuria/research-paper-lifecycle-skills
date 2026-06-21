# Diagnosis patterns: from symptom to a safe, ordered plan

How to convert the findings from [architecture-checklist.md](architecture-checklist.md)
into a restructuring plan that the author can approve and that keeps the
document coherent at every step. The five remedies — **move, merge, split,
cut, add** — each have characteristic ripple effects; a plan that ignores them
produces a paper that compiles but reads as broken.

## The reordering symptom → remedy table

For each finding write a one-line remedy in this shape so the plan is scannable:

```
[severity] <failure mode> · <where> · remedy: <move|merge|split|cut|add> · ripple: <what to fix afterward>
```

- **severity** — *blocks comprehension* (reader gets lost / a reviewer can't
  follow the argument), *weakens* (the argument survives but is harder), or
  *minor* (polish-grade).
- Lead with the *blocks-comprehension* findings; those are why the author asked.

## Ripple effects per remedy

**move** (relocate a section to where its job belongs)

- Fix every cross-reference that assumed the old order: "as shown in
  Section~\ref{...}" that now points *forward* when it used to point back (or
  vice versa). `\ref`/`\cref` resolve by label, so they won't break the
  compile, but the *prose* ("the previous section") goes wrong.
- Fix narrative connectors: a section that opened "Building on the above…" no
  longer has "the above" if it moved earlier. Flag these seams for the author
  or `polish-prose`.
- A moved Related Work changes what the reader knows at the contribution
  bullets — re-check promise-vs-delivery after the move.

**merge** (two sections doing one job become one)

- Dedupe, don't concatenate: the merged section should not say the same thing
  twice. Keep the clearer phrasing of each overlapping point; the author
  decides which.
- Reconcile the two labels — keep one `\label`, redirect references to the
  dropped one.
- The section count drops; re-check any "in the following three sections" count
  promises in the intro.

**split** (one section carrying two jobs, or holding misplaced content,
becomes two)

- The extracted unit needs its **own topic sentence** stating its (now
  explicit) job — `outline_extract.py` will flag it `NO-OPENING-PROSE` if you
  forget.
- Decide placement of the new unit deliberately (a Threats-to-Validity split
  out of Results goes *after* Results, not before).
- Give the new unit a label and wire up any references to its content.

**cut** (a section delivers nothing the paper needs)

- **Preserve the text.** A cut is a proposal; move the removed prose to a
  "cut content" note in the plan (or a scratch file) so it is recoverable —
  never silently delete the author's work.
- Rescue dependencies: a cut section may hold the *only* citation of a
  reference (now orphaned — does another section still need it?), the only
  definition of a term used later, or a figure referenced elsewhere. List each.
- Re-check promise-vs-delivery: cutting a section may orphan an intro promise.

**add** (a gap: a promised contribution with no home, or a section with no
topic sentence)

- This is the one remedy that needs *new content*, so it is a **decision for
  the author, not an action for the skill**. Present the gap; never fabricate
  the missing proof, study, dataset, or result to fill it. The real options are
  (a) the author has the material and it needs a section, (b) the work exists
  but lives in an appendix/`\input` and just needs surfacing, or (c) the
  promise should be dropped from the intro.
- For a missing topic sentence, the skill *can* propose the opening sentence
  (it states the section's existing job, inventing no claim) — but the author
  approves it.

## Sequencing the moves so the document never breaks mid-plan

Order the steps so the paper stays coherent after each one:

1. **Cuts and merges first** (they shrink and simplify, reducing what later
   moves have to carry).
2. **Splits next** (create the new units before you place them).
3. **Moves last** (reorder the now-correct set of sections).
4. **Topic-sentence and connector fixes after each structural step**, not all
   at the end — re-run `outline_extract.py` between steps to confirm the
   skeleton matches the proposed one.

Each step must be individually reversible. If a step depends on a decision the
author hasn't made (e.g. "merge only if these two really are duplicates"),
stop and ask rather than guessing.

## Distinguishing "missing" from "mislabeled / relocated"

Before declaring a gap, rule out the benign explanations — a false "this is
missing" wastes the author's time and erodes trust:

- The content may live in an `\input`/`\include` file the extractor *did*
  follow (check the `(file:line)` column — it shows the real source file). If
  you ran `--no-inputs`, re-run without it.
- A promised "ablation" may exist under a different heading ("Sensitivity
  Analysis", "Component Study"). Match on *function*, not on the exact word.
- A proof may be in an appendix with the body pointing to it — that's a valid
  structure, not a gap.

When unsure whether something is absent or just unlabeled, present both
readings and ask.

## What stays out of scope

- **Wording.** Tightening sentences, hedging, AI-tells → `polish-prose`. This
  skill flags seams it creates; it does not smooth them.
- **Venue fit.** Page budget, template, blind level, track positioning →
  `tailor-to-venue`. Get the argument right first, *then* fit it to the venue.
- **Citation reality.** A reference orphaned by a cut (a now-dangling `\cite`)
  → `verify-citations`. Never hand-add one.
- **Claim support.** A claim left without evidence — the conclusion-vs-evidence
  arc break — → `verify-claims` (claim→evidence audit). This skill flags the
  *structural* break; whether the claim is genuinely supported is that skill's
  call. Never fabricate the missing result.
- **Acceptance prediction.** A clean structure helps; it is not a verdict.
