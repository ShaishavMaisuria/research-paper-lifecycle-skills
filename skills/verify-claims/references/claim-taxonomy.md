# Claim taxonomy — what each claim type must trace to

A research claim is load-bearing when removing it would weaken the paper's
contribution or a reviewer could attack it. `claim_audit.py` sorts candidate
sentences into the four types below by the words they use. This file says, for
each type, **what counts as evidence**, **what a reviewer will do to it**, and
**how to scope it** when the evidence is thinner than the sentence.

The skill never decides whether a claim is *true* — it only tells the author
what proof the claim is promising, so the author can supply it, scope the
claim, or cut it. The judgment is always the author's.

---

## 1. Novelty claims — "first", "novel", "new", "unlike prior work"

**What they promise:** that this thing did not exist before, in some scope.

**Evidence that backs them:**
- A literature position: the specific prior work the paper improves on or
  departs from, cited, with the precise axis of difference named.
- A *scope* that makes the claim checkable. "First" is only meaningful with a
  boundary: first *to do X*, *under constraint Y*, *at scale Z*, *for setting
  W*. An unbounded "first" is a promise the author usually cannot keep.

**Standard reviewer attack:** "This was done by [paper] in [year]." A single
counterexample sinks an absolute novelty claim and damages credibility for the
rest of the paper. Reviewers enjoy finding these.

**How to scope:** narrow until the claim survives one hostile literature search.
`first to do X` → `first to do X under streaming, bounded-memory constraints`.
If even the scoped version is uncertain, prefer "to our knowledge, the first
…" — which is honest about the limit of the search, not a guarantee. Pair any
novelty claim with the citations that establish the gap (route those through
`verify-citations`).

---

## 2. Superiority claims — "outperforms", "state-of-the-art", "best", "superior"

**What they promise:** this method beats specific alternatives on a specific
measure.

**Evidence that backs them:**
- A comparison table/figure with **named baselines**, a **named benchmark/
  dataset**, a **named metric**, and the **margin** (and, ideally, variance /
  error bars across seeds, not a single run).
- Baselines that are **current and fairly tuned** — beating a weak or stale
  baseline is the most common silent overclaim.
- "State-of-the-art" specifically promises *the best known result*: it needs the
  current SOTA cited and compared, not just "better than the baselines we
  picked".

**Standard reviewer attack:** "You omitted [stronger baseline]"; "your baseline
is undertuned"; "the margin is within noise / no error bars"; "SOTA on this
benchmark is actually [higher number] from [paper]".

**How to scope:** state the comparison set explicitly ("outperforms the four
baselines in Table 2" not "outperforms existing methods"), report variance, and
reserve "state-of-the-art" for when the current best is actually cited and
beaten. If the win is on one of several metrics, say which.

---

## 3. Result / magnitude claims — "significantly", "X% improvement", "Nx faster", "substantially"

**What they promise:** a quantified effect of a stated size.

**Evidence that backs them:**
- The **exact number must appear in a table or figure** the prose summarizes,
  and the prose number must **equal** it. (`claim_audit.py --numbers` lists
  prose numerics vs. table cells for exactly this reconciliation.)
- "**Significantly**" is a *statistical* word. It needs a **named test** (t-test,
  Wilcoxon, bootstrap CI, …), the test's result, and ideally the n. A larger
  mean is not significance. If no test was run, the word must change ("notably",
  "by 3.2 points") — the data does not change.
- Speedups/ratios need the **baseline they are measured against** and the
  **conditions** (hardware, batch size, input size) stated.

**Standard reviewer attack:** "'Significant' — what test? what p-value?";
"the abstract says 12% but Table 4 says 9.6%"; "Nx faster on what hardware,
against what baseline?"; "is this within run-to-run variance?".

**How to scope / fix:** reconcile every prose number to its table (fix the
*prose*, from the table — never edit the table to flatter a sentence). Replace
"significant" with either a real test or a non-statistical word. State the
measurement conditions for any ratio.

> The classic camera-ready bug: a table is regenerated late, the numbers move,
> and a sentence in the intro/abstract still quotes the old figure. Re-run
> `--numbers` after any table change.

---

## 4. Generalization / guarantee claims — "always", "in all cases", "guarantees", "robust", "general"

**What they promise:** the result holds beyond the cases actually tested.

**Evidence that backs them:**
- A **proof** for a "guarantee" (and the assumptions stated) — for an empirical
  paper, a guarantee word usually means a theorem is expected; if there is no
  theorem, the word is wrong.
- For "robust"/"general"/"always": the **range of conditions tested** must cover
  the range claimed. Three datasets do not justify "in all settings".

**Standard reviewer attack:** "You tested 3 datasets and claim it generalizes";
"'guarantees' — where is the proof / what are the assumptions?"; "counterexample
where it fails".

**How to scope:** bound the claim to the tested envelope — "across the five
datasets we evaluate" not "in all cases"; "robust to the noise levels in §5.2"
not "robust". Reserve "guarantees" for claims with a proof and stated
assumptions.

---

## The evidence test, in one line

For every load-bearing claim ask: *if a reviewer challenges this sentence, what
in the paper do I point to?* If the answer is a specific table cell, figure,
theorem, experiment, or verified citation — `SUPPORTED`. If the pointer is
vaguer than the claim — `WEAK`, scope it. If there is no pointer — `UNSUPPORTED`,
back it or cut it. If the pointer's number disagrees with the sentence —
`MISMATCH`, reconcile from the evidence.
