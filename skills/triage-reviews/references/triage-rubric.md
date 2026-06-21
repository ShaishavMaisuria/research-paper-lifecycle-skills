# Triage rubric — classification, severity, effort, priority

How to fill the `classification`, `severity`, `effort`, `evidence_anchor`,
and `response_strategy` fields that `parse_reviews.py` leaves null, and how
`build_matrix.py` turns them into a priority order. The numeric scoring here
MUST stay in sync with `scripts/build_matrix.py`.

## Contents

- [Classification: the five categories](#classification-the-five-categories)
- [Classification decision tree](#classification-decision-tree)
- [Severity: what acceptance hinges on](#severity-what-acceptance-hinges-on)
- [Effort: what a response costs](#effort-what-a-response-costs)
- [Priority score and response bands](#priority-score-and-response-bands)
- [Response strategy per classification](#response-strategy-per-classification)
- [Reviewer-leverage heuristics](#reviewer-leverage-heuristics)
- [Budget allocation](#budget-allocation)
- [Honesty rules](#honesty-rules)

## Classification: the five categories

| Value | Meaning | Typical signal |
|---|---|---|
| `misunderstanding` | The reviewer misread the paper, or missed text that already answers the point | The answer exists verbatim in the paper; reviewer states something the paper does not say |
| `real-flaw` | The criticism is correct: an error, gap, overclaim, or missing necessary piece | You cannot point to anything in the paper that refutes it |
| `requested-experiment` | The reviewer wants new results: a baseline, ablation, dataset, metric, or rerun | "Compare against X", "what happens when", "please report", "add an ablation" |
| `clarification` | No new work needed — rewrite, define, restructure, or explain | "Unclear", "hard to follow", "please define", presentation/figure complaints, questions answerable from existing material |
| `disagreement` | A judgment call where reasonable experts differ: novelty, significance, scope, taste | "Incremental", "not interesting to this community", "I would have framed this as..." |

Exactly one value per concern. If a concern genuinely bundles two categories
(e.g. a misreading wrapped around a real gap), split it: duplicate the JSON
entry, give it the next id (e.g. `R2.4`), put the split note in `notes`.

## Classification decision tree

Apply in order; first match wins.

1. **Does the paper already contain the answer, or did the reviewer assert
   something the paper does not claim?** Find the exact section/table/line.
   Found it → `misunderstanding` (and put the location in `evidence_anchor`).
   Be strict: "we sort of imply it in 4.2" is NOT a misunderstanding — that
   is a `clarification`.
2. **Is the reviewer asking for results that do not exist yet?** →
   `requested-experiment`. This holds even if you think the experiment is
   unnecessary — record why in `notes`; the response may decline it.
3. **Is the criticism factually correct about the paper as submitted?** →
   `real-flaw`. Errors in proofs, unsupported claims, broken comparisons,
   missing related work that undermines novelty, reproducibility gaps.
4. **Could the point be fully resolved by rewriting existing content?** →
   `clarification`.
5. **Otherwise** → `disagreement`. Use sparingly: if more than ~20% of
   concerns land here, re-examine — authors systematically over-classify
   real flaws as disagreements.

## Severity: what acceptance hinges on

Severity measures threat to acceptance, NOT how annoyed the reviewer sounds.

| Value | Definition | Tests |
|---|---|---|
| `critical` | Left unanswered, this alone sinks the paper | Cited in or likely to drive the overall rating; attacks the central claim, soundness, or reproducibility; raised by the most negative or most confident reviewer; anything an AC would quote in a reject meta-review |
| `major` | Materially lowers the score but is survivable | Attacks a supporting claim or one experiment; shared by 2+ reviewers (cross-reviewer repetition escalates minor→major and major→critical) |
| `minor` | Cosmetic or peripheral | Typos, figure styling, optional extra results, curiosity questions |

Calibrate against the scores: a concern from a reviewer rating
4/possibly-reject with confidence 5 outranks the same words from a
6/accept confidence 2 reviewer.

## Effort: what a response costs

Effort scores the cost to respond credibly WITHIN the rebuttal window — not
the cost to fully fix the paper.

| Value | Definition |
|---|---|
| `low` | Quote the paper, cite existing results, or promise a wording change. Minutes to an hour |
| `medium` | New analysis of existing data, a small rerun, new pseudocode/proof sketch, a substantial rewrite promise. Hours to a day |
| `high` | New experiments, new baselines, new datasets, retraining. Days; may not fit the window at all |

If an experiment cannot finish before the rebuttal deadline, keep
`effort: high` and note the fallback in `response_strategy` (partial result,
scoped claim, or camera-ready commitment — check whether the venue allows
new results in rebuttals at all; CVPR-style venues forbid unrequested new
experiments).

## Priority score and response bands

`build_matrix.py` computes, per concern:

```
priority = severity + classification + effort
  severity:        critical=30  major=20  minor=10
  classification:  misunderstanding=+6  real-flaw=+4  requested-experiment=+3
                   clarification=+2     disagreement=+1
  effort:          low=+3  medium=+2  high=+1
```

Severity dominates (bands never cross); misunderstandings rank first within
a band because they are the cheapest score swings available; low effort wins
ties so quick wins surface early.

Bands (also computed by the script):

- **must-address** — `critical` anything, or `major` that is not a
  disagreement. These get full evidence, numbers, and the most budget.
- **should-address** — `major` disagreements, and `minor`
  misunderstandings (cheap to correct, and uncorrected misreadings
  propagate into discussion phases).
- **brief** — everything else. Batch them: "We will fix all typos and
  figure issues (R1.3, R1.6) in the revision."

## Response strategy per classification

One line per concern in `response_strategy`; these are the patterns:

- **misunderstanding** — Never say "the reviewer misunderstood". Pattern:
  re-state the fact, point to the location, quote at most one sentence:
  "Section 5.1 (lines 412-415) reports exactly this ablation; Table 4, row
  3 shows w=64." Then concede the discoverability problem: "We will make
  this prominent in Section 1."
- **real-flaw** — Concede explicitly and fast ("The reviewer is correct"),
  then scope the damage (does the main claim survive?), then give the
  concrete fix and where it lands (rebuttal, revision, camera-ready).
  Stonewalling a real flaw is the single fastest way to lose a borderline
  paper in discussion.
- **requested-experiment** — Triage three ways: (a) run it if it fits the
  window and report numbers; (b) partially run it (one dataset, one seed)
  and commit to the full version; (c) decline with a technical reason why
  it is out of scope — never decline with "space constraints" alone.
  Verify first that the venue permits new results in the rebuttal.
- **clarification** — Give the actual answer in the rebuttal (do not just
  promise to clarify), plus the concrete revision: "We will add a worked
  example after Definition 3."
- **disagreement** — One respectful, evidence-anchored paragraph at most.
  State the strongest counter-argument (adoption, downstream impact,
  what the ablation shows), explicitly accept that experts may weigh it
  differently, and move on. Long fights over taste read as defensive and
  burn budget that critical items need.

## Reviewer-leverage heuristics

- **Champion/detractor map**: from the scores, label each reviewer
  positive / borderline / negative. The borderline reviewer with high
  confidence is usually the swing vote — their concerns gain one severity
  level in your prioritization.
- **Low-confidence negative reviewers** (confidence ≤ 2) are best moved by
  crisp factual corrections, not volume.
- **Meta-reviewer / AC items** (role `meta` in the parse) outrank
  everything at the same severity: the AC writes the decision.
- **Cross-reviewer repetition** is the strongest acceptance signal in the
  data: if 2+ reviewers raise the same point, merge the concerns in your
  head but answer each reviewer where they asked it (or per venue norm, in
  a global "common response" section) — and escalate severity one level.

## Budget allocation

With `--budget N` (e.g. `--budget 10000 --budget-unit chars` for
NeurIPS-style OpenReview responses), `build_matrix.py` reserves ~15% for
the opening/closing frame and splits the rest across that reviewer's
concerns proportionally to priority, rounded to 50-char / 10-word steps.
Treat allocations as guidance: real rebuttals routinely give a critical
real-flaw half the budget. For one-page-PDF venues (CVPR), convert the
page to ~700-900 words and pass `--budget 800 --budget-unit words`.

## Honesty rules

- Severity reflects threat, not hope. Downgrading a correct criticism to
  `minor`, or relabeling a `real-flaw` as `misunderstanding`, produces a
  rebuttal that reads as evasive — reviewers re-read the paper.
- `evidence_anchor` must point to text that actually exists in the paper.
  Never anchor to content you plan to add; that goes in
  `response_strategy` as a commitment.
- Every factual claim planned for the rebuttal must be checkable against
  the paper or new results actually in hand at writing time.
