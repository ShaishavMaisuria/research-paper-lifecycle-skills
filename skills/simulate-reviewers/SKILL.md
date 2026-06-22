---
name: simulate-reviewers
description: Venue-calibrated peer-review simulation. Use when a researcher says "simulate reviewers", "mock review", "review my paper like a NeurIPS reviewer", "what would Reviewer 2 say", "red-team my paper", "find weaknesses before I submit", "peer review my paper", "strengths and weaknesses / pros and cons of my paper", "what to focus on", or wants a rubric score / borderline-reject risk estimate for a conference or journal (NeurIPS, ICML, ICLR, CVPR, KDD, SIGMOD, CHI, VLDB, LNCS, TKDE, TODS...). Builds a reviewer panel calibrated to the venue family and track (harsh NeurIPS main-track skeptics vs lenient demo-track judges), scores novelty/soundness/reproducibility/clarity on the venue's scale, hunts weaknesses grounded in quoted paper text, aggregates scores into a decision-risk band with borderline-reject flags, and outputs a prioritized fix list. Advisory only; improves the paper, never predicts the outcome, re-verifies facts against the live CFP, fabricates no citations or reviewers, and submits nothing.
---

# Simulate Reviewers

Run a paper through a simulated, venue-calibrated review panel *before*
submission. A NeurIPS main-track reviewer and a SIGSPATIAL demo-track judge
reject for different reasons at different thresholds — this skill reproduces
that difference: persona-driven weakness hunting, rubric scoring on the
venue's own scale, and a deterministic decision-risk readout that tells the
authors what to fix while there is still time.

## When to use

- "What would reviewers say about this paper?" / "simulate a review"
- "Review this like a harsh NeurIPS reviewer" / "what will Reviewer 2 hate?"
- "Is this good enough for KDD, or should I aim for the short track?"
- "Find the weaknesses before the reviewers do" / "red-team my submission"
- After `preflight-check` passes (format is clean) but before submitting —
  this skill judges *content*, preflight judges *compliance*.

## Inputs

1. The paper: a `.tex` source tree, a PDF, or a draft in any readable form.
   Process it transiently — never copy paper text into the repo.
2. A venue profile: `venues/conferences/<venue>-<year>.yml` (schema in
   `venues/schema.yml`). No profile? Create one with `parse-cfp` first, or
   run against the nearest family default and say so.
3. The target track (page limits and reviewer expectations differ — ask).

## Process

1. **Build the calibrated review packet.** Run:

   ```
   python3 scripts/review_form.py venues/conferences/<venue>-<year>.yml \
       --track "<track>"
   ```

   This is deterministic and offline. It merges the family profile and emits
   the panel (personas + harshness), the venue score scale with its
   borderline threshold, the rubric, the per-reviewer form skeleton, and a
   `scores.json` template. Add `--json` for machine-readable output. Exit
   codes: 0 ok, 2 missing/unparsable profile or unknown track.

2. **Re-verify against the live CFP — mandatory.** Profiles and the script's
   scale anchors are historical norms, never ground truth. Fetch the
   profile's `cfp_url` (and reviewer-guidelines page if linked) and confirm:
   review scale and form, blind level, rebuttal format, track expectations.
   If anything differs, update the profile YAML, note the discrepancy in the
   report, and prefer the live facts. Label every venue fact you state with a
   confidence tag and a clickable source:
   `verified-live` / `corroborated` / `inferred-from-family` /
   `needs-verification`. A scale number quoted to the user with no source is a
   bug, not a convenience.

3. **Read the whole paper and build a claim inventory.** List every claim of
   novelty ("first", "state-of-the-art", "outperforms"), every empirical
   claim, and where its supporting evidence lives. This inventory is what
   the personas attack. Method in
   [references/weakness-hunting.md](references/weakness-hunting.md).

4. **Write each review independently, in persona.** One pass per reviewer
   from the packet, in order, *without* referring to the other reviews while
   writing (real reviews are independent; convergent complaints found
   independently are the strongest signal). Persona behavior, harshness
   calibration, and track modifiers are specified in
   [references/reviewer-personas.md](references/reviewer-personas.md).
   Grounding rules — non-negotiable:
   - **Each review opens with genuine Strengths**, then Weaknesses — like a
     real review form. State 2–4 specific strengths (what the paper does well:
     novelty, a strong experiment, clarity, a useful artifact), each grounded
     in a section/figure the same way weaknesses are. A review that is all
     cons is not a real review and misleads the author about what to protect
     while fixing. Do not invent strengths to pad — if the paper is weak, say
     so, but find what genuinely works.
   - Every weakness cites a section/figure/line or quotes ≤1 sentence.
   - Never invent prior work. If a persona suspects missing related work,
     find real candidates with `find-papers` and verify them with
     `verify-citations` — or phrase the concern conditionally
     ("if prior work on X exists, R4 will find it") with no fake reference.
   - Misreadings are allowed *only* for the skimmer persona, and must be
     misreadings the actual text permits.

5. **Score with the rubric, then the venue scale.** Score the four core
   dimensions (novelty, soundness, reproducibility, clarity) 1–5 per
   reviewer using the anchors in [references/rubrics.md](references/rubrics.md),
   then map to the venue's overall scale + confidence from the packet.
   Harshness calibration: at harshness 5, an unaddressed soundness weakness
   caps the overall at borderline-reject; at harshness 2 (demo track), it
   becomes a question, not a cap.

6. **Aggregate deterministically.** Fill the `scores.json` template from
   step 1 and run:

   ```
   python3 scripts/aggregate_scores.py scores.json
   ```

   It computes the confidence-weighted mean, disagreement/champion/detractor
   flags, drag dimensions, and the decision-risk band
   (likely-reject / borderline-reject / borderline-accept / likely-accept) —
   including the "borderline without a champion resolves downward" rule.
   `--example` prints a valid input; `--json` for machine output; exit 2 on
   invalid input.

7. **Write the meta-review and the fix list.** As the AC/1AC/AE persona:
   synthesize the reviews, name the biggest shared concern, state whether a
   champion exists. Then convert every weakness into a prioritized fix list,
   each item tagged:
   - `fix-now` — addressable before submission (add ablation, soften claim,
     add reproducibility statement);
   - `rebuttal-defensible` — survivable in this venue's rebuttal format
     (check `review.rebuttal_format` / limits in the profile);
   - `structural` — cannot be fixed this cycle; consider a different
     venue/track (hand off to `select-venue`).
   Borderline-reject predictors to check explicitly are listed in
   [references/weakness-hunting.md](references/weakness-hunting.md).

## Output

A simulated review packet, presented in chat (written to a file only if the
user asks):

- **N independent reviews** in the venue's form format, each opening with a
  **Strengths** section, then **Weaknesses**, then questions and subscores.
- **The meta-review**, naming the biggest strength to preserve and the biggest
  shared risk to fix, and stating whether a champion exists.
- **The score table** plus the `aggregate_scores.py` decision-risk readout.
- **The prioritized fix list**, every item tagged `fix-now` /
  `rebuttal-defensible` / `structural`.

Every output carries the disclaimer: this is a simulation to improve the
paper, **not** a prediction of the real outcome.

## Worked mini-example

A 9-page submission to NeurIPS main track. After `python3
scripts/review_form.py venues/conferences/neurips-2026.yml --track Main` and a
live-CFP check (scale and rebuttal format confirmed, tagged `verified-live`),
the four personas are written independently. Convergence emerges: **R2** (the
empirical skeptic) and **R4** (the adjacent-field expert) both, without seeing
each other, land on the same gap.

> **R2, Weaknesses.** "Table 2 reports a single run (§5.1). With ±std over 5
> seeds, does the +1.3% gap over the baseline survive? No tuning-budget parity
> is stated for the baseline." — soundness 2, confidence 5.

> **R4, Weaknesses.** "The §1 claim 'first to combine X with Y' needs the
> 2023 work on X-under-Y. If that line exists, the novelty claim narrows to an
> engineering delta." (Conditional — routed to `find-papers`; no fake citation
> stated.) — novelty 2, confidence 4.

Filling and aggregating `scores.json` (R1 5/4, R2 4/5, R3 6/2, R4 5/4) yields:

```
conf-weighted mean: 4.8   delta vs threshold: -0.133 (normalized)
DECISION RISK:      BORDERLINE-REJECT
drag dimensions:    soundness 2.5, reproducibility 2.75
flags:              strong detractor present (R2) — objection must be rebuttal-proof
```

The fix list leads with the convergent finding: **`fix-now`** — add 5-seed
±std and tuning-budget parity to Table 2 (cheapest path off the soundness
floor); **`fix-now`** — verify the X-under-Y prior work and soften the "first"
claim accordingly. The meta-review notes the only above-threshold score came
from the low-confidence skimmer (no real champion), so at borderline this
resolves downward unless the soundness objection is closed before submission.

## Adapt to your discipline

Panels and scales are keyed on the venue `family:` field. For other fields,
fork and add a calibration entry (personas + scale) for your community in
`scripts/review_form.py` and a venue YAML — e.g. an APA-journal panel with
action-editor + 2 reviewers and accept/minor/major/reject.

## Guardrails

- Never present the simulation as a prediction ("your paper will get a 5 at
  NeurIPS"). Say: "the simulated panel scored it X; real panels vary widely."
- Never fabricate citations, reviewer identities, or quotes — personas are
  archetypes, never named real researchers; missing-related-work claims go
  through `find-papers` + `verify-citations` or stay conditional.
- Re-verify review-process facts against the live `cfp_url` (step 2 is not
  optional); flag any profile staleness in the report.
- Process the paper transiently; quote at most one sentence per finding;
  never store paper text in this repo.
- Never submit to, or post on, any review system on the user's behalf.
- Format/compliance problems found along the way are out of scope — route
  them to `preflight-check`.

## Memory

This skill uses the shared `.paper-memory/` convention in the user's paper
directory, following [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md).

- **At start:** read `.paper-memory/profile.yml` (vertical, risk appetite,
  venue tier) to calibrate the panel and how hard the personas press novelty
  claims, and read `lessons.md` to recall which weaknesses were already raised
  and which `recurring` ones this author repeats (e.g. "weak ablations" or
  "overclaimed contributions") so the meta-review leads with them.
- **At end:** append the durable weaknesses in the shared format `- [YYYY-MM-DD]
  (simulate-reviewers | <scope>) weakness -> recommendation` (via
  `reflect-and-improve`'s `reflect_log.py append`, which dedupes and dates). A
  structural habit seen across drafts is `recurring`; a draft-specific gap is
  `this-paper`. Do not log per-reviewer score noise.
- Create `.paper-memory/` on demand if absent and offer to add it to the
  project `.gitignore`. It is local-only; never upload it or copy it into this
  repo.
