---
name: simulate-reviewers
description: Venue-calibrated pre-submission peer-review simulation. Use when a researcher says "simulate reviewers", "mock review", "review my paper like a NeurIPS reviewer", "what would Reviewer 2 say", "red-team my paper", "find weaknesses before I submit", or wants a rubric score / borderline-reject risk estimate for a conference or journal (NeurIPS, ICML, ICLR, CVPR, KDD, SIGMOD, SIGSPATIAL, CHI, ICDE, VLDB, LNCS, TKDE, TODS...). Builds a reviewer panel calibrated to the venue family and track (harsh NeurIPS main-track skeptics vs lenient demo-track judges), scores novelty/soundness/reproducibility/clarity on the venue's review-form scale, hunts weaknesses grounded in quoted paper text, aggregates scores into a decision-risk band with borderline-reject flags, and outputs a prioritized fix list. Advisory simulation only — never predicts real outcomes, never fabricates citations, never submits anything.
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
   report, and prefer the live facts.

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

A simulated review packet, presented in chat (and written to a file only if
the user asks): N independent reviews in the venue's form format, the
meta-review, the score table + `aggregate_scores.py` decision-risk readout,
and the prioritized fix list. Every output carries the disclaimer: this is a
simulation to improve the paper, **not** a prediction of the real outcome.

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
