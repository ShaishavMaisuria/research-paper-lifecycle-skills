# Scoring Rubric — venue-fit conformance

The benchmark scores **measurable conformance** to award-winner/top-cited patterns. Each dimension is something you can extract from a draft and compare to a distribution measured across the exemplar corpus. Nothing here measures whether the science is good — that is out of scope by design (see SKILL.md "When NOT to use it").

## The dimensions

| # | Dimension | What is measured (extractable) | Why it correlates with strong papers |
|---|---|---|---|
| 1 | Section architecture | Presence/order of expected sections for the venue family; whether structure matches the modal exemplar layout | Winners rarely deviate from the venue's expected skeleton |
| 2 | Contribution framing | Explicit contributions list in intro; each contribution stated as a claim; positioned delta vs prior work | Award papers make contributions unmissable |
| 3 | Evaluation rigor signals | Count of baselines, ablations present (y/n), datasets count, significance/variance reporting, error bars | Strong empirical papers over-deliver on evaluation |
| 4 | Reproducibility artifacts | Code/data link present, artifact/availability statement, appendix with details | Increasingly decisive at top venues |
| 5 | Claim & citation density | Citations per page vs exemplar range; related-work coverage; **citation integrity from `verify-citations`** | Winners are well-grounded and not under/over-cited |
| 6 | Abstract structure | Presence of motivation→gap→approach→result→impact arc; quantified result in abstract; length vs venue norm | The abstract is the most-read, most-predictive surface |
| 7 | Figure/table conventions | Count and density vs exemplars; a "teaser"/overview figure present; tables use booktabs-style | Visual communication tracks with reception |
| 8 | Writing register | Hedging calibration, active contribution voice, terminology consistency (overlaps `polish-prose`) | Clarity is a measurable, learnable signal |

## How a dimension is scored (0–10)

For each dimension:
1. Measure the draft's value(s).
2. Measure the same across the exemplar corpus → get a range/median.
3. Score = how close the draft sits to the exemplar central tendency, on the conformance bands below.
4. **Always record**: draft value, exemplar range, the one-sentence basis, **and the realization level** (see next section). A score with no basis is invalid.

## On-family distribution requirement (dims 1, 5, 6, 7 especially)

Dimensions scored against a measured *distribution* — section architecture (1), claim/citation density (5), abstract structure (6), figure/table conventions (7) — must be compared to an **on-family** exemplar distribution: papers from the *same venue family* as the target. Scoring these against an off-family central tendency (e.g. judging an ACL two-column paper by a NeurIPS single-column distribution, or a SOSP/OSDI systems paper by the generic acm-sigconf proxy) silently violates the honesty rule below, because the "exemplar range" you report is then not the range for *this kind of paper*.

Resolve the on-family distribution in this priority order:

1. **A live `study-exemplars` corpus for the target venue** — always preferred; it is freshest and most specific.
2. **The family profile's `exemplar_distribution` block** in `venues/families/<family>.yml` — a fallback prior of measured bands (refs/page, figs/page, tables/page, abstract length, teaser/artifact rates, modal sections). When you use it, disclose that the bands came from the family prior rather than a live corpus, and carry its confidence (usually `inferred-from-family`).
3. **No on-family distribution exists** (no matching family profile *and* no on-family corpus): do **not** substitute another family's numbers as if they applied. Per the honesty rule, **reduce N** for these dimensions and disclose `no on-family exemplar distribution`; score them only as far as venue-agnostic structure allows (presence/absence of a contributions list, a teaser figure, an artifact statement), never against a borrowed central tendency. Pass `no_on_family_distribution: true` on those dimensions so `scorecard.py` records the disclosure.

## Staleness gate (hard format constraints)

Profiles are year-versioned via `verified.valid_window` and `verified.last_verified_against_cfp`. Do **not** assert a *hard format constraint* — page limit, column count, mandatory section, deadline — from a profile whose `valid_window` does not include the target cycle without a fresh CFP check first. A different-year (or different-host) profile may inform *priors* (the exemplar distribution, the modal skeleton) but must never be the sole basis for a hard rule. If you cannot run the freshness check, flag the constraint as `needs-verification` rather than stating it as fact, and note in the scorecard that the format basis was a year-mismatched profile. This is the rule that was violated when year-mismatched conference profiles were used to infer hard format constraints.

## Realization level (plan vs. executed) — record per dimension

A draft can be a *plan/outline* — honest `[RESULT]` placeholders where numbers will go — or a *finished* paper with the experiments run. Scoring an outline against the executed-paper bands silently punishes deliberate deferral as if the work were attempted and weak. That conflates two very different states and makes the index uninterpretable: a grader cannot tell "a plan that would pass once filled" from "a plan that would fail". To keep the honesty rule intact while making the gap read as *experiments not run* rather than *design is weak*, **record a realization level alongside the 0–10 band for every dimension**:

| Level | Meaning | How it shows up in the draft |
|---|---|---|
| `absent` | The dimension is not addressed at all | No baselines named, no eval section, no plan |
| `planned` | Designed but not yet built or run | Named baselines/datasets/ablations; matched-budget + variance/significance policy stated; results are honest `[RESULT]`/`[TBD]` placeholders |
| `drafted` | Partially realized | Some numbers in, some still placeholders; figures stubbed |
| `complete` | Fully realized | Numbers, plots, error bars, artifacts present |

The realization level is **descriptive**, not a second score — it tells the reader and `scorecard.py` how to interpret the band. Detect it mechanically: a dimension whose evidence is dominated by well-formed `[RESULT]`/`[TBD]`/`\todo`-style slots (rather than missing content) is `planned`, not `absent`.

### Scoring a `planned` dimension — grade the *design*, not absent numbers

For any dimension at `planned` level (and especially the empirical ones — evaluation rigor, reproducibility artifacts, figure/table conventions), score the **completeness and specificity of the experimental design**, never realized numbers. Concretely, for evaluation rigor at `planned`, award the band on how many of these are *specified*:

- Named baselines (not "we will compare to prior work" — actual methods)
- Named datasets / benchmarks with splits
- An explicit ablation list (which components get removed and why)
- A matched-budget / matched-compute protocol (so comparisons are fair)
- A variance / significance / error-bar policy (seeds, CIs, the test to be used)

A `planned` dimension that names all of these is a *strong, specific plan* and should score near the top of its capped band; one that hand-waves ("we will run standard baselines") scores low. Treat well-formed `[RESULT]` placeholders as a distinct **"deferred-but-specified"** state: the basis must say so explicitly (e.g. *"deferred-but-specified — full marks once slots filled"*), so the score reads as conditional, not as a realized weakness.

### Cap on planned-only dimensions

A `planned` or `absent` dimension **cannot reach the 7–8 "within range" band or above** — it is capped at 6, because "within the exemplar range" is a statement about *realized* values the draft does not yet have. The cap is enforced by `scorecard.py` so it cannot be eyeballed away. This keeps an honest no-compute reconstruction from being either over-credited (claiming conformance it hasn't earned) or unfairly floored (scored as run-and-weak). The gap to a finished winner remains visible — it just reads correctly as "experiments not run", with a clear path ("specify, then run") instead of an unexplained large negative.

### Conformance bands

| Band | Meaning (executed draft) | Meaning when the dimension is `planned` |
|---|---|---|
| 9–10 | Matches or exceeds the exemplar median on this dimension | *unreachable while planned* |
| 7–8 | Within the exemplar range, below median | *unreachable while planned* |
| 5–6 | Just outside the exemplar range; a reviewer would notice | A complete, specific design (all of baselines/datasets/ablations/budget/variance named) — deferred-but-specified |
| 3–4 | Clearly below exemplar norms; likely a weakness reviewers cite | A partial or vague design (some elements missing or hand-waved) |
| 0–2 | Absent or far off (e.g. no contributions list, no baselines) | No design at all |

For `planned`/`absent` dimensions the band is read in the right-hand column and is capped at 6 (enforced by `scorecard.py`).

## The venue-fit index

A weighted mean of the dimension scores. Default weights (venue profiles may override via a `benchmark_weights` block):

- Evaluation rigor signals ×1.5 (the most common reject reason at empirical venues)
- Contribution framing ×1.3
- Citation integrity component of dim 5 is a **gate**: any unresolved/fabricated citation caps the index at 4 until fixed, regardless of other scores. Fabricated citations sink papers; the scorecard must reflect that.
- All other dimensions ×1.0

The aggregate is computed by `scripts/scorecard.py`, never by hand.

### Plan-conformance vs. executed-conformance

The index is **mode-aware**. If any scored dimension is at `planned`/`absent` realization, the artifact is a plan, and the script labels the index **"plan-conformance"** (not plain "venue-fit") so it is *never silently compared against an executed paper's index*. A plan-conformance index answers "is this a complete, specific plan that would conform once run?", which is a different question from "does this finished paper conform?". Always report the mode next to the number, and never average a plan-conformance index together with executed ones in a leaderboard.

## Honesty rules (non-negotiable)

- The index is labeled **"venue-fit (conformance)"**, never "quality", "acceptance probability", or "award likelihood". When any dimension is `planned`/`absent`, it is further labeled **"plan-conformance"** and must not be compared against executed-paper indices.
- A plan is scored on its design, not on numbers it honestly hasn't produced. Never silently mark a deliberate `[RESULT]` placeholder as run-and-weak; record it as deferred-but-specified and say "full marks once filled". This is a copilot signal about *form and completeness*, not a verdict on deferred work.
- Report the corpus basis: how many exemplars, award vs top-cited, recency window. A score from 2 papers is weaker than from 8 — say so.
- **Score dims 1/5/6/7 on an on-family distribution, never an off-family proxy.** If no on-family distribution (live corpus or family-profile `exemplar_distribution`) exists, reduce N and disclose `no on-family exemplar distribution` for those dimensions rather than borrowing another family's central tendency.
- **Do not assert a hard format constraint from a year-mismatched profile** without a fresh CFP check (the staleness gate). Mark it `needs-verification` instead.
- Conformance can be gamed (a paper can look like a winner and be wrong). State this. The scorecard finds *gaps to fix*, it does not bless a paper.
- If exemplars could not be fetched, do not invent a distribution — reduce N and disclose, or decline to score that dimension.
