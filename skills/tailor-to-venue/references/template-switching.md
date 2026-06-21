# Template / documentclass switch plan

How to move a draft between the major CS template families without breaking
compilation or violating the target CFP. The target invocation comes from the
venue profile (`format.documentclass`) — ALWAYS re-verify it against the live
CFP and the venue's author kit; style files churn yearly.

## Contents

- [The five families](#the-five-families)
- [Universal switch procedure](#universal-switch-procedure)
- [What breaks per direction](#what-breaks-per-direction)
- [Bibliography style mapping](#bibliography-style-mapping)
- [Submission vs camera-ready flags](#submission-vs-camera-ready-flags)
- [Length conversion](#length-conversion)

## The five families

| Family | Class / package | Typical submission invocation | Columns |
|---|---|---|---|
| ACM proceedings | `acmart` | `\documentclass[sigconf,review,anonymous]{acmart}` (single-blind venues drop `anonymous`) | 2 |
| ACM manuscript (CHI-style review) | `acmart` | `\documentclass[manuscript,review,anonymous]{acmart}` | 1 |
| IEEE conference | `IEEEtran` | `\documentclass[conference]{IEEEtran}` | 2 |
| NeurIPS-style ML | `article` + venue `.sty` | `\documentclass{article}` + `\usepackage{neurips_<year>}` (ICML/ICLR analogous, options differ) | 1 |
| Springer LNCS | `llncs` | `\documentclass{llncs}` | 1 |

NEVER reuse a previous year's ML style file (`neurips_2025.sty` for a 2026
submission) — year-mismatched style files are a desk-reject trigger. Download
the current author kit from the venue site.

## Universal switch procedure

1. Take the EXACT target invocation from the venue profile, then confirm it
   on the live CFP/author kit page.
2. Start from the target template's fresh skeleton (author kit sample file),
   then transplant your content INTO it — do not mutate the old preamble in
   place; leftover redefinitions cause subtle violations.
3. Transplant in this order: title block → abstract → body sections →
   floats → bibliography → venue-mandated extras (CCS concepts, index terms,
   checklist, impact statement).
4. Reconcile packages: drop packages the target class already loads
   (`acmart` loads `hyperref`, `booktabs`, `microtype`, `libertine` fonts —
   re-loading some of them errors) and re-add what you actually use.
5. Compile, fix errors top-down, then run
   `python3 scripts/venue_diff.py <main.tex> --venue <profile> --track <T>`
   to confirm the class/options/required-blocks now match.
6. Re-run the page budget (`scripts/page_budget.py`) — column geometry
   changes the page count drastically (see Length conversion).

## What breaks per direction

### → acmart (from IEEEtran / neurips / llncs)

- **Abstract placement**: `acmart` requires `\begin{abstract}` BEFORE
  `\maketitle` — the reverse of `IEEEtran`/`llncs` habits; wrong order is a
  compile error.
- **Author blocks**: rewrite into `\author{}` + `\affiliation{\institution{}
  \city{} \country{}}` + `\email{}` per author. `\country{}` is mandatory —
  TAPS rejects without it.
- **Mandatory metadata**: add `\begin{CCSXML}...\end{CCSXML}` + `\ccsdesc{}`
  (generate at dl.acm.org/ccs) and `\keywords{}`. The ACM Reference Format
  block renders automatically; do not fake it.
- **Rights commands**: `\setcopyright`, `\acmConference`, `\acmDOI` arrive
  with the camera-ready eRights email — leave sample values at submission
  unless the CFP says otherwise.
- `acmart` forbids manual font/margin fiddling at class level — delete any
  `geometry`/`times` packages from the old preamble.

### → IEEEtran (from acmart / others)

- Author block becomes `\author{\IEEEauthorblockN{...}\IEEEauthorblockA{...}}`.
- Abstract/keywords live AFTER `\maketitle`: `\begin{abstract}` then
  `\begin{IEEEkeywords}...\end{IEEEkeywords}`.
- Section heading case convention differs (IEEEtran uppercases primary
  headings itself — don't pre-uppercase).
- `IEEEtran` does not load `hyperref`/`booktabs`; add them explicitly.
- Some IEEE venues mandate extra sections (e.g. an AI-generated-content
  acknowledgement at recent ICDE) — check `format.required_sections` and the CFP.

### → NeurIPS-style (from 2-col formats)

- Plain `article` + the year's `.sty`; submission anonymity is handled by the
  style's default (no `final` option) — there is no `anonymous` class option.
- The mandatory paper checklist section must be INSIDE the PDF after
  references (NeurIPS-style venues desk-reject without it).
- Two-column floats (`figure*`) become regular figures; resize widths from
  `\columnwidth` to `\linewidth`.
- Acknowledgments only in the camera-ready (`final`) version.

### → llncs (from any)

- `\institute{}` replaces affiliation blocks; ORCIDs commonly included.
- Abstract goes inside `\maketitle` flow per the LNCS sample; keywords use
  `\keywords{}` AFTER the abstract (3-6 keywords, 150-250 word abstract are
  Springer norms).
- Theorem environments: `llncs` predefines `theorem`, `lemma`, etc. — remove
  your own `\newtheorem` lines or you get "already defined" errors.
- Springer prohibits changing the page size/margins; the small trim size
  makes wide tables overflow — plan table redesign time.

### 2-column ↔ 1-column (any pair)

- Every `\columnwidth`-sized figure needs re-sizing; line-broken equations
  need re-breaking (2-col display width is ~3.3in vs ~5.5in+).
- Tables that fit a 1-column page rarely fit a 2-col column; budget redesign
  or rotate via the target-class-approved mechanism only.

## Bibliography style mapping

| Target | Style | Note |
|---|---|---|
| acmart | `ACM-Reference-Format` (`\bibliographystyle{ACM-Reference-Format}`) or biblatex `acmnumeric` | acmart camera-ready requires it; TAPS checks |
| IEEEtran | `IEEEtran.bst` (`\bibliographystyle{IEEEtran}`) | abbreviated first names; `IEEEabrv` strings available |
| NeurIPS-style | venue default is flexible; numeric or author-year both seen | keep one style consistently |
| llncs | `splncs04.bst` | Springer requires it for proceedings |

Switching styles re-formats every entry — recheck the reference page count in
the budget. If any entries need re-keying or new lookups, route them through
the `verify-citations` skill; never hand-type half-remembered references.

## Submission vs camera-ready flags

| Family | Submission | Camera-ready |
|---|---|---|
| acmart | add `review` (line numbers), `anonymous` if double-blind | drop both: `\documentclass[sigconf]{acmart}`; insert eRights/DOI block; TAPS rail |
| IEEEtran | `[conference]`; venue may want line numbers via its own kit | same class; validate via IEEE PDF eXpress; eCF form |
| NeurIPS-style | bare `\usepackage{neurips_<year>}` | add `[final]`; restore acknowledgments; +1 content page often allowed |
| llncs | per-CFP (often nothing special) | keep LNCS format; Springer copyright form |

Camera-ready specifics live in the `prepare-camera-ready` skill — do not
improvise the rails here.

## Length conversion

Approximate full-text capacity ratios when re-budgeting after a switch
(details and per-format words/page in references/page-budget-cutting.md):

- acmart sigconf page ≈ 1.0 IEEEtran page ≈ 1.6 NeurIPS pages ≈ 2.1 LNCS pages
  ≈ 1.9 acmart-manuscript pages.
- So: a 10-page sigconf draft ≈ 16 NeurIPS content pages — moving to a 9-page
  NeurIPS-style limit means cutting ~45%, which is a reframing decision
  (references/contribution-reframing.md), not a trimming exercise.
