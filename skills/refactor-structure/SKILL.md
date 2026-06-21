---
name: refactor-structure
description: Diagnoses and fixes a paper's argument architecture and narrative flow, independent of any venue. Checks whether the story is built in the right order, whether each section does its job, whether the intro promises what the body delivers, and whether the contribution -> evidence -> conclusion arc holds — then produces a restructuring plan (move / merge / split / cut sections) the author approves BEFORE anything is rewritten. Use when a researcher says "the structure is off", "it doesn't flow", "reviewers said it's hard to follow / disorganized / the story is unclear", "my intro over-promises", "related work is in the wrong place", "this section doesn't belong here", "reorganize my paper", "fix the narrative", or "the contributions don't match the results". Distinct from tailor-to-venue (venue/track fit, page limits, templates) and polish-prose (sentence-level wording). Bundles outline_extract.py to print the section tree + each section's opening sentence so the architecture is reviewable at a glance.
---

# Refactor Structure

Fix the *architecture* of the argument, not its words. A paper can be
grammatical, on-template, and within the page limit and still fail because the
story is assembled in the wrong order, a section doesn't do its job, the
introduction promises things the body never delivers, or the conclusion
outruns the evidence. This skill diagnoses those problems and produces a
**restructuring plan** — move / merge / split / cut, with the reasoning for
each — that the author approves before a single section is rewritten.

It plans and (on approval) executes the moves. It does not reword sentences
(that is `polish-prose`) and it does not fit the paper to a venue's rules
(that is `tailor-to-venue`).

## When to use

- "The structure feels off" / "it doesn't flow" / "reorganize my paper".
- Reviewers said: hard to follow, disorganized, the story is unclear, the
  contribution is buried, related work is in the wrong place, a section
  doesn't belong.
- The intro over-promises (claims a proof / user study / ablation the body
  doesn't contain), or the conclusion claims something never evidenced.
- Redundant sections (two Background sections), or one section doing two jobs
  (Results carrying Threats-to-Validity).

Not for: sentence wording / de-AI-ifying (`polish-prose`), page limits /
templates / track fit (`tailor-to-venue`), the Related Work section's *content*
(`draft-related-work`), or whether the citations are real (`verify-citations`).

## Inputs

- The draft: main `.tex` file (the script follows `\input`/`\include`).
- Optional: the paper's intended contribution list and target paper type, from
  `.paper-memory/profile.yml` if present (a theory paper and an empirical paper
  have different expected arcs). If absent, ask the author for the one-sentence
  claim and the contribution bullets.

## Process

### 1. Read the structure, don't re-read the paper

Run the bundled extractor to get the skeleton on one screen:

```
python3 skills/refactor-structure/scripts/outline_extract.py <main.tex>
```

It prints the section/subsection tree, each unit's **first sentence** (the
topic sentence — where a well-built section announces its job), and per-unit
signals (word count, citations, whether it carries floats/equations/lists,
units that open with *no* topic sentence). Use `--md` to drop the skeleton
into the plan, `--json` to drive your own analysis, `--no-inputs` to run on a
single section file. Exit 2 on bad input. This is a **structure map, not a
verdict** — it tells you what is where; the diagnosis below is the judgment.

### 2. Establish the intended arc

Before judging order, know what the paper is *trying* to argue. Read the
contribution bullets and the abstract's claim. Write down, in one line each:
the problem, the claimed contribution(s), the evidence that should back each
contribution, and the conclusion each contribution licenses. This is the spine
every later check measures against.

### 3. Diagnose against the architecture checklist

Work through [references/architecture-checklist.md](references/architecture-checklist.md),
which covers the seven failure modes (wrong order, a section not doing its job,
gaps, redundancy, misplaced content, intro/body mismatch, a broken
contribution -> evidence -> conclusion arc) and the standard section arcs by
paper type. The two highest-value, most objective checks:

- **Promise-vs-delivery.** For every contribution bullet and every "we
  show / we prove / we evaluate" in the intro, find the section that delivers
  it. A promised proof, user study, or ablation with no home section is a
  gap the reader (and reviewer) will hold against the paper. Conversely, list
  any major result section the intro never advertised.
- **Conclusion-vs-evidence.** Every claim in the conclusion must trace back to
  a result in the body. A conclusion that introduces a *new* claim (e.g.
  "scales to any number of nodes" with no scaling experiment) is an
  arc break — flag it as either "remove the claim" or "the body is missing the
  experiment that would support it."

See [references/diagnosis-patterns.md](references/diagnosis-patterns.md) for
how each symptom maps to a concrete remedy (move / merge / split / cut) and the
ripple effects to check (forward references, "as we show in Section~X" pointers,
a cut section's surviving citations).

### 4. Write the restructuring plan (the author approves it before any edit)

Produce, do not apply. Write `paper-workspace/writing/restructuring-plan.md`
with:

1. **Current skeleton** — the `--md` outline from step 1.
2. **Intended arc** — the spine from step 2.
3. **Diagnosis** — findings grouped by failure mode, each with: what's wrong,
   why it hurts the argument, severity (blocks comprehension / weakens it /
   minor), and the proposed remedy.
4. **Proposed skeleton** — the section tree *after* the plan, so the author
   sees the new order at a glance.
5. **Ordered move list** — each move/merge/split/cut as a discrete, reversible
   step with its ripple effects, sequenced so the document stays coherent
   between steps.

Present the diagnosis with the cheaper path called out:
often a reorder plus two merges fixes more than a rewrite. Where a symptom has
more than one reading — *is* the user study missing, or just unlabeled? — show
both and ask; never silently assume a section is
absent when it might live in an `\input` file.

### 5. Execute on approval, one step at a time

Only after the author signs off, apply the moves in order. After each
structural change, re-run `outline_extract.py` to confirm the skeleton matches
the proposed one, and fix the ripple effects the plan listed (cross-references,
"see Section~X" pointers, a moved section's label). Moving prose is mechanical;
do not silently reword it — flag any sentence that needs new connective tissue
for the author (or hand it to `polish-prose`). A reference orphaned by a cut
(a now-dangling `\cite`) routes through `verify-citations`; a claim left
without evidence — e.g. the conclusion-vs-evidence break in step 3 — routes
through `verify-claims` for a proper claim→evidence audit. Never invent a
citation or a result to patch either.

## Output

- A reviewable `paper-workspace/writing/restructuring-plan.md`: current
  skeleton -> intended arc -> diagnosis -> proposed skeleton -> ordered moves.
- On approval, the applied moves with a re-extracted skeleton confirming the
  result and a ripple-effect checklist (cross-refs, pointers, labels).
- The author decides every move; nothing is rewritten at sentence level here.

## Adapt to your discipline

The failure modes are field-agnostic; the *expected arc* is not.
[references/architecture-checklist.md](references/architecture-checklist.md)
gives CS-paper arcs (systems / ML-empirical / theory). Fork it for your field:
IMRaD for experimental science, a different placement of Related Work, a
Methods-before-Results vs. interleaved convention, or essay-style argument
structure in the humanities.

## Guardrails

- **Plan before you touch the paper.** Diagnosis and the move list come first;
  the author approves before any section is moved, merged, split, or cut.
- It restructures; it does not reword. Sentence-level edits are `polish-prose`;
  venue/track/page fit is `tailor-to-venue`. Do not silently rewrite moved
  prose — flag seams for the author.
- Never fabricate a result, section, or citation to "fill a gap." A missing
  user study is reported as missing; the fix is to add the work or drop the
  promise, never to invent it.
- Never delete content the author may want; a cut is a *proposal*, and cut text
  is preserved (note where it went) so it is recoverable.
- Diagnosis is from reading the structure, not from a venue rule or memory; the
  extractor's output and the draft are ground truth. It never claims the
  restructure will get the paper accepted.
- Never submit anything anywhere on the author's behalf.

## Relationship to other skills

- `tailor-to-venue` — venue/track fit, page budget, template, blind level.
  Run *after* the argument is sound; structure-then-fit, not the reverse.
- `polish-prose` — sentence-level wording, hedging, AI-tells. Run *after* the
  structure is settled, so you polish prose you're keeping.
- `draft-related-work` — the *content* of the Related Work section; this skill
  only decides where that section sits and whether it does its job.
- `verify-claims` — when a conclusion claim outruns the evidence (an arc
  break), this skill flags the structural break; `verify-claims` audits whether
  the claim is actually supported. `verify-citations` is the separate check that
  a `.bib` entry resolves (e.g. a reference orphaned by a cut).
- `simulate-reviewers` / `assess-paper` — if a mock review flagged "hard to
  follow", this skill is the fix.

## Memory

Uses the shared `.paper-memory/` convention in the user's paper directory
(full spec: [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `profile.yml` (paper type sets the expected arc) and
  `lessons.md` — lead with any recurring structural habit already recorded
  (e.g. "you habitually bury Threats to Validity in Results") so you check for
  it first.
- **At end:** append durable findings via `reflect-and-improve`'s
  `reflect_log.py append` in the shared format `- [YYYY-MM-DD]
  (refactor-structure | <scope>) pattern -> recommendation`. A habit seen
  across drafts is `recurring`; a one-off is `this-paper`. Don't log routine
  single moves.
- Create `.paper-memory/` on demand and offer to add it to the project
  `.gitignore`; it is local-only and never uploaded or copied into this repo.
