# Contribution-type → track fit, and the shortlist scoring rubric

How to classify what kind of paper the user actually has, map it to the
right track archetype, and score candidate venues into a defensible ranking.

## Table of contents

- [Contribution taxonomy](#contribution-taxonomy)
- [Track archetypes and what they reward](#track-archetypes-and-what-they-reward)
- [Mapping table](#mapping-table)
- [Scoring rubric (0-10)](#scoring-rubric-0-10)
- [Tie-breakers and red flags](#tie-breakers-and-red-flags)

## Contribution taxonomy

Classify the paper as ONE primary type (ask the user if ambiguous — the
answer changes the shortlist more than the topic does):

| Type | Telltale signs |
|---|---|
| **Novel method/algorithm** | new technique + theoretical or empirical superiority claims |
| **Theory** | proofs are the contribution; experiments minor or absent |
| **System/tool** | built artifact, architecture sections, end-to-end evaluation |
| **Dataset/benchmark** | the data or the benchmark IS the contribution |
| **Experiment/reproducibility study** | re-evaluates existing methods under controlled comparison |
| **Application/industrial experience** | deployment story, lessons learned, real-world constraints |
| **Vision/position** | argues a direction; no complete evaluation |
| **Demo** | something attendees can interact with |
| **Early-stage/short** | promising but incomplete result |
| **Survey** | synthesis of a field — usually a journal target, not a conference |

## Track archetypes and what they reward

- **Research track** — novelty + rigor. Default for methods/theory. Largest
  page budgets (7-12p excl refs at the profiled venues).
- **Applied/industry track** — real deployment evidence over novelty. Often
  shorter (e.g. SIGSPATIAL Industrial 5-10p excl refs, ICDE I&A short 6p).
- **Datasets & benchmarks track** — documentation quality, licensing,
  hosting plan, ethics. NeurIPS and KDD have dedicated tracks; elsewhere
  dataset papers compete (badly) in research tracks.
- **Experiment/reproducibility track** — fair methodology over novelty.
  VLDB "Experiment, Analysis & Benchmark" (the category tag is a mandatory
  title suffix — see the profile), EDBT "Experiments & Analysis";
  SIGSPATIAL folds these into the Research track, and its 2025 CFP required
  an "[Experiment]"-style title suffix — confirm the current rule on the
  live CFP.
- **Vision/Blue-Sky track** — provocation quality (SIGSPATIAL Vision 4p incl
  refs, KDD Blue Sky 5p excl refs, ICDM Blue Sky 4p excl refs, VLDB Vision
  6p excl refs, ICML Position track).
- **Demo track** — interactivity; tiny budgets (4p incl refs is the norm).
- **Short/poster track** — early results; some venues let reviewers demote
  research submissions to poster (SIGSPATIAL does — a soft landing).

## Mapping table

Primary type → tracks to score, in order of natural fit:

| Contribution type | First-choice track | Also consider |
|---|---|---|
| Novel method/algorithm | Research | short/poster if results are thin |
| Theory | Research (theory-friendly venue) | journal if proofs exceed page budget |
| System/tool | Research (systems-friendly) or Industry | Demo as a companion submission |
| Dataset/benchmark | Datasets & Benchmarks | Research only where no D&B track exists |
| Experiment/repro study | Experiments/Analysis track | Research with [Experiment] labeling |
| Application/industrial | Industry/Applications | Research only with a genuine methodological delta |
| Vision/position | Vision / Blue Sky / Position | workshop if no such track |
| Demo | Demo | — |
| Early-stage/short | Short/poster | workshop at the flagship venue |
| Survey | Journal (e.g. survey-friendly: TKDE allows 20p surveys) | not conference tracks |

A "companion submission" (paper to Research + Demo of the same system) is
normal and allowed at most venues — but check the venue's dual-submission
policy in the profile before suggesting it.

## Scoring rubric (0-10)

Score every candidate venue-track pair; sort descending; show the scores.

| Dimension | Points | Anchors |
|---|---|---|
| **Topic fit** | 0-3 | 3 = this community publishes directly on the topic (name 2-3 recent related papers from the venue if possible); 2 = adjacent; 1 = plausible stretch; 0 = wrong community |
| **Track fit** | 0-3 | 3 = contribution type matches the track archetype above; 1 = mismatch the user would have to write around; 0 = track rewards the opposite of what the paper has |
| **Prestige fit** | 0-2 | 2 = venue tier matches the work's maturity AND the user's stated goals (CORE/CCF/h5 per `ranking-sources.md`); 1 = over- or under-shooting; 0 = clear mismatch |
| **Deadline feasibility** | 0-2 | 2 = comfortably makes the next deadline (from `scripts/list_venues.py`) given the user's readiness; 1 = tight but possible; 0 = passed or unreachable — note the next cycle instead |

Do not let prestige outvote fit: the rubric caps prestige at 2 of 10 by
design. State each score with a one-line justification — the justifications
are the deliverable, the numbers just order it.

## Tie-breakers and red flags

Tie-breakers, in order: (1) sooner reachable deadline; (2) page budget vs
the draft's current length (a 12p draft fits ICDE's 12p excl refs without
surgery; cutting to 8p for KDD costs weeks); (3) blind level vs the user's
situation (an already-public preprint is awkward at double-blind venues —
check the venue's preprint policy in the CFP); (4) rebuttal/revision format
the user can actually staff; (5) logistics: attendance mandates (ICDE 2026
requires an author to register and present in person; SIGSPATIAL's 2025 CFP
mandated registration + in-person presentation — check the live CFP), visa
lead time, open-access fees.

Red flags that veto a venue regardless of score: resubmission embargoes
(ICDE rejects carry a 1-year embargo), per-author submission caps, the
paper already being under review elsewhere (dual-submission bans), and any
unverified critical fact — if the live CFP could not be checked, say so in
the shortlist rather than presenting the venue as confirmed.
