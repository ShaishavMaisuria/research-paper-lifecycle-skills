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
4. **Always record**: draft value, exemplar range, and the one-sentence basis. A score with no basis is invalid.

### Conformance bands

| Band | Meaning |
|---|---|
| 9–10 | Matches or exceeds the exemplar median on this dimension |
| 7–8 | Within the exemplar range, below median |
| 5–6 | Just outside the exemplar range; a reviewer would notice |
| 3–4 | Clearly below exemplar norms; likely a weakness reviewers cite |
| 0–2 | Absent or far off (e.g. no contributions list, no baselines) |

## The venue-fit index

A weighted mean of the dimension scores. Default weights (venue profiles may override via a `benchmark_weights` block):

- Evaluation rigor signals ×1.5 (the most common reject reason at empirical venues)
- Contribution framing ×1.3
- Citation integrity component of dim 5 is a **gate**: any unresolved/fabricated citation caps the index at 4 until fixed, regardless of other scores. Fabricated citations sink papers; the scorecard must reflect that.
- All other dimensions ×1.0

The aggregate is computed by `scripts/scorecard.py`, never by hand.

## Honesty rules (non-negotiable)

- The index is labeled **"venue-fit (conformance)"**, never "quality", "acceptance probability", or "award likelihood".
- Report the corpus basis: how many exemplars, award vs top-cited, recency window. A score from 2 papers is weaker than from 8 — say so.
- Conformance can be gamed (a paper can look like a winner and be wrong). State this. The scorecard finds *gaps to fix*, it does not bless a paper.
- If exemplars could not be fetched, do not invent a distribution — reduce N and disclose, or decline to score that dimension.
