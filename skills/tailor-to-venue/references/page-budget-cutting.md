# Page-budget cutting plan

How to take a draft from N pages to the track limit without desk-reject risk
and without gutting the contribution. Use `scripts/page_budget.py` output as
the input: it tells you how far over you are and which sections are bloated.

## Contents

- [Rules before cutting](#rules-before-cutting)
- [What counts toward the limit](#what-counts-toward-the-limit)
- [The cutting ladder](#the-cutting-ladder)
- [Density facts per format](#density-facts-per-format)
- [Forbidden moves (desk-reject triggers)](#forbidden-moves-desk-reject-triggers)

## Rules before cutting

1. Recompile and re-measure after EVERY pass — page_budget.py estimates are
   ±20%; the PDF is ground truth.
2. Cut in plan order (ladder below): structural moves first, prose last.
   Cutting prose before structure wastes effort you may undo.
3. Confirm from the profile (and the live CFP) what is EXCLUDED from the
   limit; cutting references at a refs-excluded venue is free pain.
4. Record every cut in a "restore list" — camera-ready usually grants +1-2
   pages (profile `camera_ready.extra_pages`) and journals invite extensions.

## What counts toward the limit

Always read `tracks[].page_limit_excludes` in the profile, then verify on the
CFP. Patterns seen across the shipped profiles:

| Pattern | Typical venues | Consequence for cutting |
|---|---|---|
| refs + appendix excluded | SIGMOD/SIGSPATIAL research-style | appendix is a free overflow valve (mind per-venue appendix caps, e.g. SIGSPATIAL allows up to 2 appendix pages) |
| refs excluded only | ICDE-style | appendix material must fit or go to supplementary/arXiv |
| nothing excluded | most demo/short/vision tracks | every reference and caption costs space |
| refs + appendix + checklist excluded | NeurIPS-style | the mandated checklist is free; content pages are the only constraint |
| word/length norms instead of hard limit | CHI-style manuscript | "contribution weighed relative to length" — cut for reviewer goodwill, not compliance |

## The cutting ladder

Apply top to bottom; estimate savings after each rung with page_budget.py.

### Rung 1 — structural exports (cheapest, ~0.5-2+ pages)

- Move proofs, extra ablations, hyperparameter tables, and dataset details to
  the appendix IF the track excludes appendix pages, else to supplementary
  material or a cited technical report/arXiv version (mind anonymity — see
  references/anonymization-sweep.md before adding an arXiv link).
- Delete a secondary contribution outright if it has its own section and the
  track reframing (references/contribution-reframing.md) no longer needs it.

### Rung 2 — floats (~0.25-0.5 page each)

- Merge same-axis plots into one multi-curve figure; merge per-dataset tables
  into one table with dataset columns.
- Demote full-width (`figure*`/`table*`) floats to single-column where legible.
- Convert a simple architecture figure to a short paragraph, or a small
  results table to two sentences.
- Trim caption prose — captions of 5+ lines are body text in disguise.
- Crop whitespace inside included graphics (the PDF bounding box, not LaTeX
  scaling) and prefer `[t]` placement; LaTeX packs top-placed floats tighter.

### Rung 3 — section-level prose (targets from page_budget.py cut candidates)

- Related work: group citations by theme, one sentence per theme
  ("Grid-based methods [3,7,9] adapt resolution statically"). Typical save:
  0.3-0.7 page.
- Introduction: cut the second example and the paragraph that previews what
  Section N contains (the contributions list already does this).
- Method: replace re-derivations with a citation; inline trivial equations;
  collapse enumerated design alternatives you rejected into one sentence.
- Evaluation: keep the experiments that support the lead claim of the CHOSEN
  track; summarize the rest in one "additional results" paragraph pointing to
  appendix/supplementary.
- Delete "In this section, we..." topic sentences and "As mentioned above"
  back-references throughout.

### Rung 4 — line-level compression (last, ~0.2-0.5 page total)

- Hunt widows: a paragraph whose last line holds 1-2 words yields a full line
  when shortened by a few words.
- De-duplicate: the same caveat stated in intro, method, and discussion keeps
  one home.
- Replace nominalizations ("provides an improvement of" → "improves").
- Abbreviate after first use, consistently.

### If still over after Rung 4

The paper is too big for the track. Either retarget to a longer-limit track
(see the "other tracks" table in venue_diff.py output) or split the work.
Do not proceed to forbidden moves.

## Density facts per format

Rule-of-thumb full-text capacity (no floats), matching page_budget.py
constants — use for "how much must go" arithmetic only:

| Format | ~words/page | ~refs/page |
|---|---|---|
| acmart sigconf (2-col) | 980 | 34 |
| IEEEtran conference (2-col) | 1000 | 36 |
| acmart manuscript (1-col, CHI review) | 520 | 22 |
| NeurIPS-style (1-col) | 620 | 26 |
| LNCS (llncs) | 460 | 30 |

Implication when SWITCHING templates: a 9-page NeurIPS draft is ~6 pages of
sigconf, but 12 LNCS pages hold less than 6 sigconf pages. Recompute the
budget AFTER the template switch, not before.

## Forbidden moves (desk-reject triggers)

Never include these in a cutting plan — venues explicitly desk-reject for
template tampering (SIGSPATIAL, Springer/LNCS, and most ACM venues state this
in the CFP):

- `\vspace` with negative values around sections/floats
- changing margins, `\textheight`, `\textwidth`, or paper size
- font size/family changes, `\baselineskip`/`\linespread` tweaks
- `\small` (or smaller) applied to body text, captions, or references
- redefining `\section` spacing via `titlesec` or manual `\titlespacing`
- moving REQUIRED content (limitations, ethics, checklist items) into
  excluded appendix space when the CFP says it must be in the main body

Legal and safe: `\paragraph{}` instead of `\subsubsection{}` where the class
allows it, `booktabs` tables (often shorter than vertical-ruled ones), and
venue-permitted compact bibliography styles — confirm against the CFP, and
flag anything borderline for the `preflight-check` skill before submission.
