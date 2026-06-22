# Rubric anchors and venue score scales

Scoring spec for the simulation: the four core rubric dimensions (scored 1–5
per reviewer), how subscores map to an overall score, and the per-family
overall scales emitted by `scripts/review_form.py`.

> Scale anchors are **historical norms**. Venues change forms and ranges
> year to year. Always re-verify against the live CFP / reviewer guidelines
> (the `cfp_url` in the venue profile) before relying on a scale.

## Table of contents

- [Core rubric dimensions (1–5)](#core-rubric-dimensions-15)
- [Mapping subscores to an overall score](#mapping-subscores-to-an-overall-score)
- [Venue overall scales](#venue-overall-scales)
- [Confidence / expertise](#confidence--expertise)

## Core rubric dimensions (1–5)

Score each dimension per reviewer. Anchors below; interpolate for 2 and 4.

### Novelty / originality

| Score | Anchor |
|---|---|
| 1 | Already published (or an obvious trivial variant); the "this is just X + Y" reduction fully applies |
| 3 | Incremental but real delta over the closest prior work, and the paper says honestly what the delta is |
| 5 | Opens a problem, technique, or result the community does not have; survives the adjacent-field expert's search for prior art |

Checks: claim inventory items tagged "first/novel/state-of-the-art"; the
related-work section's coverage of the *closest* (not just famous) work;
whether the delta is stated or left for the reviewer to guess.

### Technical soundness

| Score | Anchor |
|---|---|
| 1 | Central claim does not follow: flawed proof, broken experimental design, or baseline strawmanned |
| 3 | Main claims supported; secondary claims under-supported (missing ablation, single dataset, stats absent but plausible) |
| 5 | Claims, assumptions, and evidence in one-to-one correspondence; ablations per component; significance/variance reported; fair baselines |

Checks: every claim in the inventory has evidence at the cited location;
assumptions stated where used; numbers in abstract/conclusion match the
tables; tuning budget parity; the hard datasets are present or their absence
justified.

### Reproducibility

| Score | Anchor |
|---|---|
| 1 | Could not be re-implemented: key hyperparameters/data/procedures missing, no artifact plan, private data with no fallback |
| 3 | Re-implementable with effort; most settings given; artifacts "available on request" or promised |
| 5 | Code/data available (anonymized at double-blind venues), versions and seeds pinned, hardware stated, checklist (where mandated) fully answered |

Checks: artifact statement; dataset versions; the venue's own instrument
(NeurIPS checklist, SIGMOD ARI, journal data policies — see the profile's
`format.required_sections`).

### Clarity / presentation

| Score | Anchor |
|---|---|
| 1 | The skimmer persona cannot state the contribution after reading abstract + intro + figures |
| 3 | Understandable with re-reading; some undefined notation or overloaded figures |
| 5 | Contribution findable in the first page; figures self-contained; notation defined before use; tables readable without the text |

Checks: run the skimmer pass first and record what it got wrong — each
misreading is a clarity finding with a location.

## Mapping subscores to an overall score

There is no formula a real reviewer follows; use these rules:

1. **Soundness gates.** At harshness ≥4, soundness ≤2 caps the overall at
   the scale's borderline-reject step regardless of other dimensions. A
   beautiful, novel, broken paper is a reject.
2. **Novelty gates at flagship research tracks.** At harshness 5,
   novelty ≤2 caps the overall one step below threshold ("well executed but
   known" is a NeurIPS rejection archetype).
3. **Reproducibility rarely lifts, often sinks.** Reproducibility 1 costs
   one overall step at harshness ≥4; reproducibility 5 is expected, not
   rewarded.
4. **Clarity moves the variance.** Low clarity does not directly reject,
   but it makes the skimmer mis-score everything else — reflect that in the
   skimmer's overall, not in everyone's.
5. **Track emphasis overrides.** Demo/industry/vision tracks re-weight per
   the track modifier notes in the packet (e.g. demo: a soundness 3 with a
   working artifact outscores a soundness 4 with no demo plan).

## Venue overall scales

Emitted per family by `review_form.py`; thresholds drive
`aggregate_scores.py`.

### `ml-conf-10` — NeurIPS-style (historical norm)

1 trivial/wrong · 2 strong reject · 3 clear reject · 4 reject ·
5 borderline reject · **6 borderline accept (threshold)** · 7 accept ·
8 strong accept · 9 very strong accept · 10 award quality.
ICLR has used a 1/3/5/6/8/10 recommendation set in past years; ICML's form
changes by year. Re-verify the current form on OpenReview before quoting
numbers to the user.

### `pc-conf-6` — generic PC scale (ACM SIG / IEEE conferences)

1 strong reject · 2 reject · 3 weak reject · **4 weak accept (threshold)** ·
5 accept · 6 strong accept.
The real widget is submission-system dependent: EasyChair commonly −3..+3,
HotCRP 1–5 "overall merit", CMT venue-defined. The simulation uses this
6-point scale internally; translate when presenting if the user knows their
venue's actual form.

### `chi-5` — CHI A/ARR/RR/RRX/X (verified for CHI 2026; re-verify each year)

5 = A (Accept) · 4 = ARR (accept, required minor revisions) ·
3 = RR (Revise & Resubmit, ~4–5-week window — CHI 2026's was ~4 weeks;
check the year's dates) · 2 = RRX (R&R unlikely to
succeed) · 1 = X (Reject). Threshold 3.5: RR is genuinely borderline — up
to ~half of R&R papers are rejected in round 2.

### `journal-4` — journal recommendations (TKDE/TODS-style)

4 accept · 3 minor revision · **2 major revision** · 1 reject.
Threshold 2.5: "major revision" keeps the paper alive at the cost of a full
extra cycle, and a second major revision often becomes a reject. For
extension papers, insufficient delta over the conference version is a
soundness *and* novelty finding.

## Confidence / expertise

Each review carries a confidence (used as the weight in
`aggregate_scores.py`):

- NeurIPS-style: 1–5 (5 = "absolutely certain, checked the math/code").
- Conference PC / CHI / journals: 1–4 expertise (4 = expert in this exact
  area).

Assign confidence in persona: the adjacent-field expert is confident about
novelty but not proofs; the skimmer's confidence is low by construction
(2 at most) — which is exactly why a paper that only the skimmer likes is
in danger.
