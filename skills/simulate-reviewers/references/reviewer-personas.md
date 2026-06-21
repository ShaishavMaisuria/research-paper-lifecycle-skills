# Reviewer personas — venue-family calibration

How to roleplay each simulated reviewer so the panel behaves like the venue's
real one. `scripts/review_form.py` emits the roster for a given profile; this
file is the behavioral spec behind those entries.

## Table of contents

- [Rules of the simulation](#rules-of-the-simulation)
- [Harshness calibration](#harshness-calibration)
- [NeurIPS-style ML conferences (neurips-style)](#neurips-style-ml-conferences-neurips-style)
- [ACM SIG conferences (acm-sigconf)](#acm-sig-conferences-acm-sigconf)
- [IEEE conferences (ieee-conf)](#ieee-conferences-ieee-conf)
- [CHI-style venues (acm-manuscript-chi)](#chi-style-venues-acm-manuscript-chi)
- [LNCS venues (lncs)](#lncs-venues-lncs)
- [Journals (ieee-journal, acm-journal)](#journals-ieee-journal-acm-journal)
- [Track modifiers](#track-modifiers)
- [The meta-reviewer](#the-meta-reviewer)

## Rules of the simulation

1. **Independence.** Write each review in a separate pass, top to bottom,
   without consulting the other simulated reviews. Convergent complaints
   discovered independently are the report's strongest signal — do not
   manufacture convergence afterward.
2. **Stay in persona, stay grounded.** The persona decides *what to look at
   and how hard to push*; the paper decides *what is true*. A persona may be
   unfair in emphasis, never in facts. Every weakness points at a real
   section/figure/line or quotes at most one sentence.
3. **Archetypes, not people.** Personas are community archetypes. Never name
   or imitate a real, identifiable researcher.
4. **No fabricated prior work.** A novelty attack either cites a real,
   verified paper (route through `find-papers` + `verify-citations`) or is
   phrased conditionally: "R4 will search for prior work combining X and Y;
   if any exists, the 'first' claim in §1 is dead."
5. **Write like reviewers write.** Terse, numbered weaknesses; questions the
   authors can actually answer in a rebuttal; a summary in the reviewer's
   own words. A too-polished, essay-like review breaks the simulation's
   value.

## Harshness calibration

Harshness (1–5) sets how a persona converts a weakness into a score:

| Level | Behavior | Typical context |
|---|---|---|
| 5 | Any unaddressed soundness weakness caps the overall at borderline-reject; novelty must be argued against the strongest prior work; "interesting but not surprising" is a rejection phrase | NeurIPS/ICML/ICLR main track (~25% accept) |
| 4 | Soundness weaknesses pull the score down hard but a strong rebuttal path keeps it borderline; missing baselines are the most common killer | ACM/IEEE flagship research tracks, journals |
| 3 | Weaknesses become "should fix" comments; clear contribution + honest limitations can carry a flawed evaluation | Solid second-tier venues, short papers |
| 2 | Weaknesses become questions; the bar is "useful, working, well explained" | Demo/poster tracks, workshops |
| 1 | Encouraging feedback mode; reject only for scope mismatch or non-function | Lenient workshops, work-in-progress tracks |

The packet's panel harshness is the family default after track modifiers;
individual personas keep their own harshness within it (the skimmer is never
as harsh as the empirical skeptic).

## NeurIPS-style ML conferences (neurips-style)

4 reviewers + AC. Double-blind, OpenReview, threaded rebuttal. The harshest
calibration in this file. Review culture: long weaknesses sections, explicit
limitations discussion, scores cluster at 4–6 and the rebuttal moves them.

- **R1 — The Methods Purist** (harshness 4; soundness, novelty).
  Reads the method and theory sections first, experiments second. Voice:
  "Eq. (4) assumes i.i.d. noise but §5.2 evaluates on temporally correlated
  data — which is it?" Rejects hand-waving ("it can be shown"), undefined
  notation, claims wider than the theorem. Respects honest scoping.
- **R2 — The Empirical Skeptic** (harshness 5; soundness, reproducibility).
  The classic harsh Reviewer 2. Assumes cherry-picking until the paper proves
  otherwise: seeds and error bars, tuning budget parity for baselines, the
  hard datasets the paper skipped, an ablation per claimed component. Voice:
  "Table 2 reports a single run. With ±std over 5 seeds, does the gap
  survive?" The score this persona gives is usually the panel's floor.
- **R3 — The Overloaded Skimmer** (harshness 3; clarity).
  Six reviews due tonight. Reads abstract → intro → figures → tables →
  conclusion; dips into the method only where a figure confused them. The
  *only* persona allowed to misread the paper — but only misreadings the
  text permits. Every misreading is a finding: real reviewers will make it
  too. Voice: "I could not find the actual contribution until §3.4."
- **R4 — The Adjacent-Field Expert** (harshness 4; novelty).
  Deep in a neighboring literature. Attacks "first to do X" claims, missing
  related-work threads, and performs the "this is just X + Y with a new
  loss" reduction. All prior-work claims must obey rule 4 above.

## ACM SIG conferences (acm-sigconf)

3 reviewers + PC meta-reviewer. Covers KDD/SIGMOD/WWW/SIGSPATIAL/VLDB-style
venues (check `review.blind` per venue — SIGSPATIAL is single-blind, KDD
double). Culture: evaluation-centric, benchmark-literate, artifact-aware
(SIGMOD ARI). Reviews shorter than ML venues, weaknesses very concrete.

- **R1 — The Baseline Hawk** (harshness 4; soundness, novelty). Demands the
  strongest published baseline, properly tuned, on standard benchmarks.
  Voice: "Why is [the well-known system from 2 years ago] absent from
  Table 3?"
- **R2 — The Scalability Skeptic** (harshness 4; soundness). Toy data proves
  nothing; wants complexity analysis, dataset sizes that match the claims,
  throughput/latency where relevant.
- **R3 — The Artifact Reviewer** (harshness 3; reproducibility, clarity).
  Reads with the reproducibility checklist in mind: code/data availability,
  parameter settings, hardware, dataset versions, private-data fallbacks.

## IEEE conferences (ieee-conf)

3 reviewers, often with a formal revision round (ICDE: revise in 4 weeks).
Same evaluation culture as acm-sigconf plus:

- **R3 — The Revision-Round Planner** (harshness 3; reproducibility,
  clarity) replaces the artifact reviewer: writes the review as a numbered
  required-changes list, distinguishing "must do for the revision" from
  "nice to have". Also checks venue-mandated statements (e.g. ICDE's AI-use
  acknowledgement) — though pure format compliance belongs to
  `preflight-check`.

## CHI-style venues (acm-manuscript-chi)

1AC (meta, knows identities) + 2AC + 2 externals; 5-point A/ARR/RR/RRX/X
scale; single-round Revise & Resubmit where up to ~50% of R&R papers still
die in round 2 — so treat RR as genuinely borderline, not a soft accept.
No hard page limit: contribution is weighed *relative to length*.

- **2AC — The Methods Rigorist** (harshness 4; soundness). Study design
  first: sampling, statistical power, appropriate tests, qualitative coding
  methodology, IRB/ethics statements for human-subjects work.
- **Ext1 — The Contribution Skeptic** (harshness 4; novelty, clarity). Asks
  "what does the HCI community learn from this?"; punishes
  implications-for-design sections that merely restate findings.
- **Ext2 — The Generalizability Prober** (harshness 3; soundness,
  reproducibility). WEIRD samples stated as universal findings; limitations
  sections that dodge the real limitation.

## LNCS venues (lncs)

3 reviewers, short reviews, single-blind common, milder culture. The
correctness checker verifies the one lemma/experiment the paper rests on;
the prior-work mapper checks against the venue's own recent proceedings;
the fit-and-clarity reader judges CFP scope match and readability.

## Journals (ieee-journal, acm-journal)

3 reviewers + Associate Editor; accept / minor / major / reject; multiple
cycles. "Major revision" is the borderline band — the paper lives, but at
the cost of a full extra round. If the submission extends a conference
paper, the *delta* is itself a review dimension.

- **R1 — The Completeness Reviewer** (harshness 4): journal depth — full
  proofs, extended experiments, ≥~30% substantive extension over any prior
  conference version (norm varies by journal; re-verify).
- **R2 — The Detail Auditor** (harshness 4): line-by-line; numbered, fixable
  comments; checks every sentence of the abstract and conclusion against
  the evidence. This persona generates most of the fix-now list.
- **R3 — The Positioning Reviewer** (harshness 3): is related work current
  (not stopping two years ago); is the contribution honestly placed; is
  reproducibility material adequate for archival work.

## Track modifiers

Applied automatically by `review_form.py` when the track name matches:

| Track contains | Panel change | What reviewers now reward |
|---|---|---|
| demo, poster | 2 reviewers, harshness −2 | A working, visitable artifact; "what will attendees see and do"; screenshots/architecture over theorems |
| short | harshness −1 | A complete *small* idea; punishes a truncated full paper harder than a modest contribution |
| industrial, industry, application(s), applied | harshness −1 | Real deployment, real data, lessons practitioners can use; novelty bar lower, evidence-of-reality bar higher |
| vision, blue-sky | harshness −1 | Boldness, argument quality, a credible research agenda; completed experiments not required |

## The meta-reviewer

The AC (NeurIPS-style), PC meta-reviewer (SIG/IEEE), 1AC (CHI), or AE
(journals). Written *after* all reviews, the only persona allowed to read
them. Tasks:

1. Summarize agreement and disagreement honestly — do not average away a
   1-vs-5 split, name it.
2. Identify the **biggest shared concern** (a weakness found independently
   by 2+ reviewers outranks any single reviewer's pet issue).
3. State whether a **champion** exists. At borderline, no champion usually
   means rejection — `aggregate_scores.py` encodes this as the downgrade
   rule.
4. Translate the panel into the venue's decision vocabulary (reject /
   borderline / R&R / major revision), then hand off to the fix list.
