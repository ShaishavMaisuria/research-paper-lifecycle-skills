# Weakness hunting — taxonomy and borderline-reject predictors

The systematic method behind step 3–4 of the skill: build a claim inventory,
then sweep the paper once per weakness category. Every finding must carry a
location (section/figure/table/line) or a quote of at most one sentence.

## Table of contents

- [The claim inventory](#the-claim-inventory)
- [Weakness taxonomy](#weakness-taxonomy)
- [Borderline-reject predictors](#borderline-reject-predictors)
- [Grounding and honesty rules](#grounding-and-honesty-rules)
- [From weaknesses to the fix list](#from-weaknesses-to-the-fix-list)

## The claim inventory

Before any persona pass, read the full paper once and table every claim:

| # | Claim (quoted ≤1 sentence) | Location | Type | Evidence location | Evidence sufficient? |
|---|---|---|---|---|---|

Claim types: `novelty` ("first", "novel", "unlike all prior work"),
`superiority` ("outperforms", "state-of-the-art", "X% better"),
`generality` ("works for any...", "in real-world settings"),
`efficiency` ("scales to", "real-time"), `theoretical` (theorems, bounds).

The abstract, intro contributions list, and conclusion are claim-dense;
harvest them line by line. A claim with no evidence row is already a
finding.

## Weakness taxonomy

Sweep once per category; assign each finding to the persona whose emphasis
matches (see [reviewer-personas.md](reviewer-personas.md)).

### W1 — Claim–evidence gaps / overclaiming

"State-of-the-art" with no comparison to the actual SOTA; "real-world" with
synthetic data; abstract numbers that differ from the tables; generality
claimed from one domain. Severity: high at harshness ≥4. Usually `fix-now`
(soften the claim) — the cheapest score points in the whole report.

### W2 — Missing or weak baselines

The strongest published competitor is absent, outdated, or under-tuned;
baselines run with default settings while the method is tuned; no simple
baseline (the "linear model / nearest-neighbor would get 90% of this"
attack). Severity: the most common single killer at evaluation-centric
venues. `fix-now` if the baseline is runnable before the deadline,
otherwise `rebuttal-defensible` only with a credible reason.

### W3 — Experimental design

Single seed / no error bars / no significance tests; benchmark selection
that omits the hard or standard datasets; metrics chosen to flatter; no
ablation for a claimed component; train/test leakage risks; scale of data
inconsistent with scalability claims. Severity: high; at harshness 5 this
is R2's score floor.

### W4 — Novelty deltas

The "X + Y" reduction; closest prior work cited but not compared; closest
prior work *not* cited (verify candidates via `find-papers` before
asserting — see grounding rules); a "first to" claim that is only first
within an unstated qualifier. Severity: gates the overall at flagship
research tracks; mild at demo/industry tracks.

### W5 — Reproducibility holes

No code/data statement; missing hyperparameters, hardware, dataset
versions; private data without a public fallback; checklist answers
(where mandated) inconsistent with the paper body. Almost always `fix-now`:
a reproducibility paragraph is cheap and reviewers notice its absence.

### W6 — Clarity and structure

Contribution not findable in pages 1–2; Figure 1 does not explain the
method; undefined notation; tables that need the text to decode; section
order that buries the main result. Record the skimmer persona's actual
misreadings — each is a concrete clarity finding with a location.

### W7 — Related-work blind spots

Threads from adjacent communities missing; survey stops 2+ years ago;
self-citation clusters replacing engagement with others' work. Candidates
for "missing" papers MUST be real: search with `find-papers`, verify with
`verify-citations`, or phrase conditionally. Never put a fabricated
reference in a simulated review.

### W8 — Scope and fit

Topic outside the CFP's listed areas; contribution type mismatched to the
track (research paper in a demo track or vice versa); paper length
mismatched to contribution (CHI judges this explicitly). Often `structural`
— the fix is `select-venue`, not edits.

## Borderline-reject predictors

After scoring, check these explicitly — they separate "borderline-accept"
from "borderline-reject" at real PC meetings, and `aggregate_scores.py`
encodes the first two:

1. **No champion.** Nobody scored clearly above threshold. Borderline
   papers without a champion usually die in discussion (the aggregator
   downgrades borderline-accept to borderline-reject when spread is high
   and no champion exists).
2. **A confident detractor.** One well-below-threshold score from a
   high-confidence reviewer outweighs two lukewarm accepts; the rebuttal
   must be aimed at *that* objection.
3. **Convergent weaknesses.** The same weakness found independently by 2+
   personas (especially a W2/W3) — ACs read convergence as ground truth.
4. **Rebuttal-proof objections.** Weaknesses that cannot be answered within
   the venue's rebuttal format (`review.rebuttal_format` / `rebuttal_limit`
   in the profile): e.g. "needs a new human study" at a venue with a
   10,000-character text-only rebuttal. These should dominate the fix list.
5. **Skimmer failure.** If the skimmer persona mis-stated the contribution,
   assume one real reviewer will too — at borderline, a misunderstood paper
   loses the discussion.
6. **Checklist/limitations dissonance** (venues with mandated instruments):
   answers that contradict the paper body invite a soundness objection on
   top of the compliance one.

## Grounding and honesty rules

- Location or ≤1-sentence quote for every finding. No location, no finding.
- Never invent experimental results, prior work, or reviewer quotes.
- Missing-related-work findings: real verified candidates or conditional
  phrasing. Route through `find-papers` + `verify-citations`.
- Only the skimmer persona may misread, and only misreadings the actual
  text permits; label them as misreadings in the report.
- Severity must reflect the venue calibration in the packet, not a generic
  standard — re-verify the venue facts against the live CFP first.

## From weaknesses to the fix list

Convert every finding into one fix-list row:

| Priority | Finding (persona, location) | Tag | Suggested action |
|---|---|---|---|

- `fix-now` — doable before the deadline: soften W1 claims, add the W5
  reproducibility paragraph, restructure the intro for W6, add a missing
  ablation if compute allows.
- `rebuttal-defensible` — survivable in this venue's rebuttal format; note
  *how* (which evidence, which character budget). Hand the actual rebuttal
  to `triage-reviews` / `write-rebuttal` after real reviews arrive.
- `structural` — wrong venue/track or a missing study; hand to
  `select-venue` or plan for the next cycle.

Order by: rebuttal-proof objections first, then convergent weaknesses, then
single-persona findings; within a tier, cheapest fix first.
