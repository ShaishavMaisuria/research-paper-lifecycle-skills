# Architecture checklist

The seven ways a paper's argument architecture fails, and the standard
section arcs to measure against. This is a diagnosis aid for
`refactor-structure`, not a venue rulebook — none of it depends on a specific
conference. (Venue/track/page concerns live in `tailor-to-venue`.)

Read the skeleton from `outline_extract.py` first, then walk these checks
against it and the draft.

## The seven failure modes

### 1. Wrong order — the story is assembled out of sequence

The reader should never need information they haven't been given yet. Classic
order faults:

- **Related Work before the Introduction.** The reader meets prior work before
  the problem is framed, so the comparisons are meaningless. Related Work
  belongs *after* the problem is established (right after the intro, or — common
  in ML/CHI — moved to just before the conclusion so the contribution lands
  first).
- **Method before motivation.** A design section that opens before the reader
  knows what problem it solves.
- **Results before the setup that interprets them.** Numbers with no
  experimental setup, baselines, or metrics defined yet.
- **Definitions used before they are introduced.** A term load-bearing in
  Section 3 first defined in Section 5.

*Signal in the skeleton:* the order of headings, and topic sentences that
reference something not yet established ("As shown above…", "Recall the
threshold…") earlier than the thing they reference.

### 2. A section that doesn't do its job

Every section has a job, announced by its **first sentence**. If the topic
sentence doesn't state the section's purpose, the section probably drifts.

- A "System Design" section whose opening sentence is about evaluation.
- A unit that opens with a figure or a subsection and has **no topic
  sentence** at all (the extractor flags this as `NO-OPENING-PROSE`). The
  reader has no idea what the section is for until they've read it.
- A section that is one paragraph long (under-developed) or that sprawls across
  three sub-arguments (should split).

*Signal:* the printed first sentence vs. the heading; word-count outliers
(a 600-word "Conclusion", a 40-word "Evaluation").

### 3. Gaps — something the argument needs is missing

- A contribution with no section delivering it (see Promise-vs-delivery below).
- A claim with no evidence section.
- A method with no evaluation, or an evaluation with no method described.
- Missing connective sections the reader expects for the paper type (e.g. no
  Threats to Validity in an empirical systems paper, no Limitations where the
  field expects one).

### 4. Redundancy — the same job done twice

- Two sections that say the same thing under different names ("Background" and
  "Preliminaries" that restate each other) — **merge candidate.**
- A point made fully in the intro and again in full in a later section.
- The conclusion re-deriving the results rather than synthesizing them.

*Signal:* near-identical topic sentences; two adjacent low-word-count sections
covering the same ground.

### 5. Misplaced content — right material, wrong section

- Threats to Validity / Limitations buried inside Results instead of being its
  own unit.
- A design decision argued inside Related Work.
- An experimental detail that belongs in Setup sitting in the Discussion.

The fix is usually **split** (extract the misplaced material into its own unit)
or **move** (relocate it to the section whose job it is).

### 6. Intro promises ≠ body delivers (the most reviewer-visible fault)

Reviewers read the contribution bullets, then check the body delivers each
one. The intro is a contract.

- The intro claims a **formal proof**, a **user study**, an **ablation**, a
  **new dataset**, or **N baselines** — and the body has no section for it.
- The intro **under-sells**: a major results section the contributions never
  advertised (the reader doesn't know to look for the paper's best result).
- Contribution bullets in a different order than the body presents them, so the
  reader's mental map is wrong.

This check is concrete and high-value: enumerate every "we prove / we show / we
evaluate / we release" in the intro and contribution list, and point each at
the section that delivers it. Anything unmatched is a gap or an over-promise.

### 7. Broken contribution -> evidence -> conclusion arc

The spine of the paper. For each contribution there must be a chain:

```
contribution (intro)  ->  evidence (a results/proof/study section)  ->  conclusion (synthesis)
```

Arc breaks:

- **Conclusion outruns evidence.** A conclusion claim with no result behind it
  — e.g. "scales to any number of nodes" with no scaling experiment. Remedy:
  remove the claim, or flag that the body is missing the experiment.
- **Evidence with no contribution.** A whole results section that doesn't map
  to any stated contribution (why is it here?).
- **Contribution with no conclusion.** A contribution proven in the body but
  never synthesized at the end (the reader doesn't get the payoff).

## Standard section arcs by paper type

The *expected* skeleton differs by paper type — measure the draft against the
right one. (Field-specific; fork for your discipline.)

**Systems / empirical CS.**
Intro (problem + contributions) -> [Related Work] -> Background/Motivation ->
Design/Architecture -> Implementation -> Evaluation (setup -> results) ->
Threats to Validity -> Discussion -> Related Work (if not earlier) ->
Conclusion. Related Work sits either right after the intro or just before the
conclusion; Threats to Validity is its own unit, not folded into Results.

**ML / empirical learning.**
Intro + contributions -> Related Work (often late, just before conclusion) ->
Problem Setup / Preliminaries -> Method -> Experiments (setup, main results,
ablations) -> Limitations -> Conclusion. Ablations are expected and are usually
promised in the intro; a missing ablation against an intro promise is a gap.

**Theory / proofs.**
Intro + contributions -> Related Work -> Preliminaries/Definitions -> main
Theorems with proofs (or proof sketches; full proofs in an appendix) ->
Discussion/Implications -> Conclusion. A promised proof must have a home; if
it's in an appendix, the body must point to it.

**Survey / position.**
Different arc entirely (taxonomy-driven, no Method/Evaluation) — judge order
and redundancy, not promise-vs-evidence in the same way.

## How to turn a finding into a remedy

| Symptom | Remedy |
|---|---|
| Section in the wrong place | **move** |
| Two sections, same job | **merge** |
| One section, two jobs / misplaced content inside it | **split** |
| Section that delivers nothing the paper needs | **cut** (preserve the text) |
| Promised thing has no section | **add** the work, or **drop** the promise (never fabricate) |
| Conclusion claim with no evidence | **remove** the claim, or surface the missing experiment |
| Section with no topic sentence | **add** an opening sentence stating its job |

See [diagnosis-patterns.md](diagnosis-patterns.md) for sequencing the moves and
catching ripple effects.
