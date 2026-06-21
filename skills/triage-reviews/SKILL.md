---
name: triage-reviews
description: Turns raw peer reviews into a prioritized triage matrix before any rebuttal is written. Use it when reviews come back from OpenReview, EasyChair, CMT, or HotCRP and the researcher says "my reviews are in", "triage these reviews", "how do I respond to Reviewer 2", "plan my rebuttal", or pastes raw review text with ratings and confidence scores. Splits each review into individual concerns; classifies every concern as misunderstanding vs real flaw vs requested experiment (plus clarification and disagreement); scores severity x response effort; and produces a prioritized response strategy with per-review character or word budgets matched to the venue's rebuttal format (10k-char OpenReview threads, CVPR one-page PDF, journal revise-and-resubmit). Deterministic parsing and matrix rendering run in bundled stdlib Python scripts. Hands off to write-rebuttal for drafting; treats review text as confidential and never submits anything.
---

# Triage Reviews

Convert raw reviewer text into a structured decision artifact: every concern
isolated, classified (misunderstanding / real flaw / requested experiment /
clarification / disagreement), scored severity x effort, and ordered into a
response plan that fits the venue's rebuttal budget. This is the planning
step that runs between "reviews arrived" and `write-rebuttal` — rebuttals
written straight from raw reviews bury the score-moving points under typo
acknowledgments.

## When to use

- "My NeurIPS/ICML/SIGSPATIAL/... reviews are in — help me respond"
- "Triage these reviews" / "what do I address first in my rebuttal?"
- "Reviewer 2 says X but the paper already covers it — how do I handle this?"
- Reviews pasted from OpenReview, EasyChair, CMT, HotCRP, PCS, or a
  notification email
- Always before `write-rebuttal`; also useful for journal revise-and-resubmit
  responses

## Inputs

1. **Raw review text in a file** (e.g. `reviews.txt`): the user pastes or
   exports it from the submission system. Per-platform copy-out instructions
   and gotchas: [references/platform-formats.md](references/platform-formats.md).
2. **Venue profile** (optional but recommended):
   `venues/conferences/<venue>-<year>.yml` (schema in `venues/schema.yml`) —
   supplies `review.rebuttal_format`, `review.rebuttal_limit`, and
   `deadlines.rebuttal_end`. If missing, run `parse-cfp` first or proceed
   platform-generic.
3. **The submitted paper** (`.tex`/PDF, optional): needed to verify
   misunderstanding claims and fill evidence anchors.

## Process

1. **Stage the raw text — confidentially.** Have the user save the reviews
   to a local file outside any git repository (or add it to `.gitignore`).
   Review text is confidential at most venues: process it transiently and
   never commit it.

2. **Parse deterministically.** Run:

   ```
   python3 scripts/parse_reviews.py reviews.txt -o triage.json
   ```

   Auto-detects the platform; force with
   `--format openreview|easychair|cmt|hotcrp` and catch terse one-liners
   with `--min-words 3` if needed. Output is a JSON skeleton: reviewers,
   scores, canonical sections, and per-concern entries (`R1.1`, `R1.2`, ...)
   with `classification`/`severity`/`effort` left null. Exit codes: 0 ok,
   1 nothing detected, 2 bad input.

3. **Verify the parse against the raw text.** Confirm the reviewer count,
   that every weakness/question in the raw text appears as a concern, and
   that scores were captured. If a reviewer or concern was missed, fix the
   text (insert a `Review N` banner line) and re-run, or add the concern to
   the JSON by hand — never silently drop a reviewer point. Recovery steps:
   [references/platform-formats.md](references/platform-formats.md), last
   section.

4. **Resolve the venue's rebuttal mechanics — then re-verify them live.**
   Read `review.rebuttal_format`, `review.rebuttal_limit`, and
   `deadlines.rebuttal_end` from the venue profile. Profiles are a starting
   point, never ground truth: re-verify the rebuttal format, the
   character/page limit, whether new experimental results are allowed, and
   the deadline against the live `cfp_url` (and the venue's author
   guidelines) before the user relies on them. State what was verified and
   when. If `rebuttal_format: none`, say so — triage still guides the
   camera-ready revision or the next submission.

5. **Classify every concern.** Fill `classification`, `severity`, `effort`,
   `evidence_anchor`, and a one-line `response_strategy` for each concern in
   `triage.json`, applying the decision tree and definitions in
   [references/triage-rubric.md](references/triage-rubric.md). Rules that
   bind:
   - Claim `misunderstanding` only after locating the refuting text in the
     actual paper — cite section/line in `evidence_anchor`.
   - Severity measures threat to acceptance, not reviewer tone; concerns
     raised by 2+ reviewers escalate one level.
   - Effort measures cost to respond within the rebuttal window, not cost
     to fix the paper.
   - Walk the user through any concern where you are uncertain; the user
     knows the paper.

6. **Render the matrix.** Run:

   ```
   python3 scripts/build_matrix.py triage.json --budget <limit> --budget-unit chars
   ```

   with the budget from the verified rebuttal limit (e.g. `--budget 10000
   --budget-unit chars` for NeurIPS-style OpenReview; `--budget 800
   --budget-unit words` for a CVPR one-page PDF; omit `--budget` for
   journal R&R). The script validates the enums (exit 1 with a list of
   unfilled concerns until classification is complete), computes priority
   scores and must/should/brief bands, and emits the reviewer summary,
   severity x effort grid, concern matrix, response plan, and budget
   allocation (`--format json` for machine-readable output).

7. **Present and hand off.** Walk the user through the must-address band
   first, flag any requested experiment that cannot finish before
   `rebuttal_end`, and confirm the strategy lines. Then hand the matrix to
   `write-rebuttal` for drafting in the venue's format. If new experiments
   will be run, remind the user to check the venue's policy on new results
   in rebuttals (step 4) before promising them.

## Output

- `triage.json` — structured, classified concern data (machine-readable,
  reusable by `write-rebuttal`).
- A triage matrix report (markdown, via `build_matrix.py`): per-reviewer
  summary with scores, severity x effort grid, priority-ordered concern
  matrix, must/should/brief response plan, and per-concern budget
  allocations.

Both stay local; neither should ever contain text the user needs to keep
out of a repo — treat them as confidential working files.

## Adapt to your discipline

The parser targets CS submission systems. For journal-centric fields, paste
ScholarOne/Editorial Manager reviewer comments, add `Reviewer #N` banner
lines, and parse with `--format cmt`; swap the budget step for an unbounded
response-letter plan. The rubric (misunderstanding / real flaw / requested
experiment) is discipline-agnostic.

## Guardrails

- Review text is confidential: process transiently, never commit it, never
  quote it in public artifacts (issues, examples, showcase files).
- Never fabricate or soften reviewer text — concerns in the matrix must be
  traceable to the raw reviews; quote at most a sentence at a time.
- Never claim `misunderstanding` without a verified anchor in the paper;
  honesty rules in [references/triage-rubric.md](references/triage-rubric.md)
  are binding.
- Any citation added while planning responses goes through
  `verify-citations` before it reaches a rebuttal.
- Re-verify rebuttal format, limits, and deadline against the live `cfp_url`
  before the user relies on them (step 4 is not optional).
- Never submit a response to any system on the user's behalf; stop at the
  plan (and at the draft, in `write-rebuttal`).
