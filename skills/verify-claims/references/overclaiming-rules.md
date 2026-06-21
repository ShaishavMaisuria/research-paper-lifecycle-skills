# Overclaiming rules — the high-frequency offenders and their fix

`claim_audit.py` surfaces candidate claims; this file is the triage manual for
the ones that most often sink papers in review. For each: what the marker
flags, when it is genuinely a problem, and the **back / scope / cut** remedy.

The three honest moves, always — and never a fourth:

- **Back it** — point to evidence already in the paper, add a verified citation,
  or run the experiment that proves it.
- **Scope it** — narrow the wording to what the evidence actually supports.
- **Cut it** — delete the claim if it cannot be backed or scoped.
- **NEVER** fabricate a result, a number, a baseline, a citation, or a
  significance test to make the sentence survive. An honest "unsupported" is
  always better than a laundered overclaim.

---

## "first" / "the first to" / "the only"

**Flagged because:** absolute primacy claims are the single highest-risk
sentence in a paper — one reviewer-supplied counterexample discredits it and
casts doubt on the rest.

**Real problem when:** there is no stated scope, or the scope is so broad a
quick search finds prior work. "The first system for graph learning" almost
certainly is not.

**Remedy:**
- *Scope* to a defensible boundary: "the first to do X *under constraint Y*".
- *Hedge the search limit* honestly: "to our knowledge, the first …".
- *Back* with the citations establishing the gap (verify them via
  `verify-citations`).
- *Cut* if neither a scope nor a citation makes it defensible.

---

## "state-of-the-art" / "SOTA" / "outperforms" / "best" / "superior"

**Flagged because:** these promise a comparison the paper must actually contain.

**Real problem when:** baselines are unnamed, stale, or undertuned; the metric
or benchmark is unspecified; no margin or variance is given; or "state-of-the-
art" is claimed without citing and beating the current best.

**Remedy:**
- *Back*: name the baselines, benchmark, metric, and margin; report variance
  across seeds, not a single run; cite the current SOTA you beat.
- *Scope*: "outperforms the four baselines in Table 2" rather than "outperforms
  existing methods"; "best among the compared methods on [metric]".
- *Cut* "state-of-the-art" specifically if the current best is not cited and
  beaten — downgrade to "competitive with" or "improves over our baselines".

---

## "significantly" / "significant" / "substantial" / "dramatic"

**Flagged because:** "significant" is a statistical term reviewers read
literally.

**Real problem when:** the word implies a test that was not run; the effect is a
single-run mean difference; the gain may be within run-to-run variance.

**Remedy:**
- *Back*: run and name a test (t-test, Wilcoxon, bootstrap CI), report its
  result and n. Then "significantly" is earned.
- *Scope*: if no test was run, replace with a non-statistical word and a number
  — "improves accuracy by 3.2 points", "notably faster". Change the **word**,
  never the data.
- Note: the fix here is almost never "cut" — it is "say what you actually
  measured".

---

## Magnitude / ratio words — "X% improvement", "Nx faster", "orders of magnitude"

**Flagged because:** a quantified claim must equal the table it summarizes and
state its measurement conditions.

**Real problem when:** the prose number disagrees with the table (stale number
after a table revision), or the baseline/hardware/input size for a ratio is
unstated.

**Remedy:**
- *Back/reconcile*: run `claim_audit.py --numbers`; for every prose number,
  confirm it matches the table cell it summarizes. Fix the **prose from the
  table** (or from the underlying result) — never the table from the prose.
- *Scope*: state the baseline and conditions for any speedup ("2.3x faster than
  [baseline] on a single A100, batch 32").

---

## Generalization words — "always", "in all cases", "general", "robust", "guarantees"

**Flagged because:** they extend the result past what was tested.

**Real problem when:** the tested envelope is narrower than the claim, or
"guarantees" appears with no proof.

**Remedy:**
- *Scope*: bound to the tested range — "across the five datasets we evaluate",
  "robust to the noise levels in §5.2".
- *Back*: for "guarantees", supply the theorem and state its assumptions; if
  there is no proof, the word is wrong.
- *Cut* the universal quantifier when neither holds.

---

## Quick triage table

| Marker | Default suspicion | First move |
|---|---|---|
| first / only | absolute primacy unbacked | scope to a constraint; add citations |
| SOTA / outperforms | comparison incomplete | name baselines+metric+margin; cite current best |
| significantly | no test behind a statistical word | run a test, or swap the word |
| X% / Nx | prose number ≠ table; conditions unstated | reconcile via `--numbers`; state conditions |
| always / guarantees | claim exceeds evidence | scope to tested range; supply proof |

## Stop condition

Re-run after edits. Stop when every load-bearing claim is `SUPPORTED`, `SCOPED`,
or a `WEAK` the author explicitly accepts and will defend — not on an open-ended
"keep softening" loop (it drifts the author's voice). Two passes is usually
enough; report whatever stays open rather than over-editing.
