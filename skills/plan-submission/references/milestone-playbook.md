# Milestone Playbook — backwards planning from a conference deadline

Reference for the `plan-submission` skill. Everything here is the
*default* playbook; the venue profile and the live CFP always win on
conflicts. Facts below were compiled from 2025–2026 CFPs (NeurIPS, ICML,
CHI, SIGSPATIAL, SIGMOD, ICDE, CVPR) — re-verify anything critical against
the target venue's own pages before the user acts on it.

## Table of contents

1. [The backwards-planning method](#1-the-backwards-planning-method)
2. [Default offset table](#2-default-offset-table)
3. [T-21d — Dual-submission audit](#3-t-21d--dual-submission-audit)
4. [T-21d — Reciprocal-reviewing check](#4-t-21d--reciprocal-reviewing-check)
5. [T-14d — Submission-system accounts](#5-t-14d--submission-system-accounts)
6. [T-10d — Author-list freeze and metadata](#6-t-10d--author-list-freeze-and-metadata)
7. [Abstract registration (its own hard deadline)](#7-abstract-registration-its-own-hard-deadline)
8. [T-5d — Supplementary material and code](#8-t-5d--supplementary-material-and-code)
9. [T-3d to T-0 — Deadline-day mechanics and AoE math](#9-t-3d-to-t-0--deadline-day-mechanics-and-aoe-math)
10. [After submission: under-review and camera-ready phases](#10-after-submission-under-review-and-camera-ready-phases)

## 1. The backwards-planning method

Anchor on the **paper deadline** from the venue profile, then place every
preparatory task at a fixed offset *before* it. Two kinds of rows:

- **HARD** — external dates the venue enforces (abstract registration,
  paper deadline, rebuttal window, camera-ready). Never movable; when one
  has passed, it is PASSED, and the plan must say what that implies.
- **PREP** — internal tasks at default offsets. Movable; when one is
  behind schedule it is OVERDUE and goes to the top of the plan.

When today is already inside the schedule (e.g. 6 days before the
deadline), do not compress every milestone proportionally — triage:
anything account- or registration-related happens *immediately* (lead
times are external and fixed), writing tasks compress.

## 2. Default offset table

| Offset | Kind | Milestone |
|---|---|---|
| T-21d | PREP | Dual-submission audit across all co-authors |
| T-21d | PREP | Reciprocal-reviewing check; name the reviewing author |
| T-14d | PREP | Submission-system accounts for EVERY author |
| T-10d | PREP | Freeze author list and order; collect ORCIDs, conflicts |
| abstract date (or T-7d) | HARD/PREP | Abstract registration |
| T-5d | PREP | Supplementary + code package within size limits |
| T-3d | PREP | Desk-reject preflight (run the `preflight-check` skill) |
| T-2d | PREP | Upload a complete draft PDF as placeholder |
| T-1d | PREP | Final PDF + supplementary; metadata matches PDF |
| T-0 | HARD | Paper deadline (state the timezone) |

`scripts/build_timeline.py` emits exactly these; this file explains them.

## 3. T-21d — Dual-submission audit

The earliest milestone because the fix (withdrawing or de-overlapping a
manuscript) takes weeks and involves other people.

- Quote the profile's `review.dual_submission` policy **verbatim** to the
  user — paraphrase can invert compliance meaning.
- Inventory: every manuscript with author overlap that is (a) under review
  anywhere archival, (b) planned for submission during this venue's review
  period, or (c) a "thin-slice" sibling of this paper. NeurIPS-style
  policies ban all three; submitting elsewhere *during* review is also a
  violation, so the audit covers the whole review window, not just the
  deadline.
- Usually fine (but verify per venue): arXiv preprints, non-archival
  workshop versions.
- Venue-specific traps: ICDE imposes a 1-year resubmission embargo on
  rejected papers and caps submissions per author (6 across its two
  rounds); NeurIPS forbids submitting the same paper to two of its own
  tracks at once.

## 4. T-21d — Reciprocal-reviewing check

ML venues increasingly require authors to review as a condition of
submission. Mishandling this can desk-reject the *paper*, which is why it
sits three weeks out:

- **NeurIPS-style:** designated author-reviewers are blocked from seeing
  their own paper's reviews until their assigned reviews are submitted;
  negligent or missing reviews can lead to rejection of the authors' own
  submissions.
- **ICML 2026** introduced a cap on how many papers may name the same
  reciprocal reviewer — a lab submitting many papers must spread the duty.
- Action at this milestone: decide *who* on the author list will review,
  confirm they meet the venue's qualification bar (publication history in
  the venue's ecosystem, complete OpenReview profile), and block their
  calendar for the review period.
- Non-ML venues (SIGSPATIAL, CHI, SIGMOD) generally have no reciprocal
  duty — the milestone is then a one-line confirmation, not a task.

## 5. T-14d — Submission-system accounts

Two weeks out because one lead time is genuinely that long: **new
OpenReview profiles registered with non-institutional emails go through
manual moderation that can take up to ~2 weeks**. Details per system in
[submission-systems.md](submission-systems.md) — at this milestone:

- Every author (not just the submitter) creates/verifies an account on the
  profile's `review.submission_system`, using the email they want on the
  paper.
- OpenReview venues typically require *complete* profiles for all authors
  (affiliation history, DBLP import, conflict domains) — an incomplete
  co-author profile at the deadline is a real failure mode.
- Confirm the submission site is actually open (profiles record the
  `submission_url`; ICML 2026 opened its OpenReview site 20 days before
  the deadline and recommended account creation on day one).

## 6. T-10d — Author-list freeze and metadata

Most venues forbid adding or removing authors after the submission
deadline (NeurIPS allows reordering but not changes to the set). Abstract
registration locks the list even earlier at many venues. So freeze at
T-10d:

- Final author set and order, affiliations, and the exact email each
  author's system account uses.
- ORCIDs: ICDE requires ORCIDs for all authors at *submission*; ACM's
  camera-ready eRights form requires ORCIDs for all authors eventually —
  collect them now either way.
- Conflict-of-interest data: institutions (current + recent), co-authors
  (typical windows: past 3 years co-authorship; advisor/advisee ever),
  and any PC members with personal conflicts. Missing COI declarations are
  an explicit desk-reject at ICDE-style venues.

## 7. Abstract registration (its own hard deadline)

At most ML/data venues the abstract is a separate, **earlier, hard**
deadline — miss it and the paper cannot be submitted at all. Observed
gaps: NeurIPS 2026 abstract May 4 vs paper May 6 (2 days); SIGSPATIAL
abstract one week before the paper; CHI metadata one week before the PDF.

What "registering the abstract" actually requires:

- Title and abstract text (placeholder-quality is tolerated at some venues
  but the title should be near-final — it drives reviewer bidding).
- Complete author list (often locked from this point).
- Subject areas / primary+secondary topics (drive reviewer assignment —
  choose deliberately, not last-minute).
- Conflicts of interest entered in the system.
- At PCS venues (CHI), the metadata deadline also locks the subcommittee
  choice — a strategic decision, see
  [submission-systems.md](submission-systems.md).

If the profile has `deadlines.abstract: null`, the timeline script emits a
T-7d PREP milestone instead, with an instruction to confirm in the CFP
whether a separate abstract deadline exists.

## 8. T-5d — Supplementary material and code

Size limits and packaging rules are venue-specific and enforced by the
upload form — discovering them at T-0 wastes deadline-day hours:

- **NeurIPS-style:** ONE submission PDF (paper + appendices + checklist),
  max 50MB; supplementary code/data as a separate ZIP, max 100MB; no
  external links to results/code except anonymized code repositories where
  the venue explicitly allows them.
- **SIGMOD-style:** optional appendix as a *separate PDF*, not appended.
- **Double-blind venues:** the supplementary must be anonymized too —
  PDF metadata, notebook outputs with usernames, README author lines, git
  history in zipped repos, hardcoded paths (`/home/alice/...`). Use an
  anonymized repository service for code links where permitted.
- Licenses and datasets: ML checklists ask about dataset licenses and
  consent — verify before packaging, not after reviews arrive.
- Action: build the package at T-5d, then run the venue's own upload form
  early (T-2d) to catch size/format rejections.

## 9. T-3d to T-0 — Deadline-day mechanics and AoE math

- **T-3d:** run the `preflight-check` skill (page budget vs profile,
  documentclass options, anonymization leaks, required checklist/impact
  statement sections). Three days leaves room to cut half a page.
- **T-2d:** upload a *complete draft* to the submission system. Submission
  systems slow down and occasionally fall over in the final hours; a
  placeholder upload converts a system outage from catastrophe to
  annoyance. Verify the uploaded PDF opens, fonts embed, and form metadata
  (title/abstract/authors) matches the PDF exactly.
- **T-1d:** final PDF + supplementary re-upload; re-check the
  "ready/complete" state of the submission (see the HotCRP gotcha in
  [submission-systems.md](submission-systems.md)); save/screenshot the
  confirmation email and submission number.
- **AoE math:** "Anywhere on Earth" = UTC−12. A deadline of May 6 AoE
  expires when May 6 ends at UTC−12, i.e. **11:59 UTC on May 7** (07:59 ET,
  04:59 PT, 13:59 CEST, 20:59 JST — next day). Safe rule: treat the
  deadline as *your local* midnight on the deadline date and bank the
  remainder as buffer. Not every venue uses AoE: SIGSPATIAL states 11:59 PM
  **Pacific Time** — always read `deadlines.timezone` from the profile and
  confirm on the CFP.

## 10. After submission: under-review and camera-ready phases

The timeline script switches phases automatically when the paper deadline
is in the past.

**Under review:**

- Rebuttal windows are short (NeurIPS 2026: ~1 week of author discussion;
  ICML 2026: Mar 30–Apr 7). Pre-block the window on every author's
  calendar at RS−7d, line up who runs any extra experiments, and re-read
  the venue's rebuttal format/limit from the profile
  (`rebuttal_format`, `rebuttal_limit`) — 10,000 characters per review at
  NeurIPS-style venues, strict one-page PDF at CVPR-style venues.
- The dual-submission policy still binds during the whole review period.
- Hand off actual rebuttal writing to `triage-reviews` + `write-rebuttal`.

**Camera-ready:**

- Start the rail at C−14d, not C−2d: the **ACM rail** (eRights form →
  ORCIDs for ALL authors → rights/DOI block inserted → source upload to
  TAPS) can take *weeks* end-to-end; the **IEEE rail** needs PDF eXpress
  validation with the conference ID, exact title/author match on the eCF,
  and conference-specific file naming. Hand off to `prepare-camera-ready`
  for the step-by-step.
- Most conferences require author registration (often at the full/member
  rate) before camera-ready upload, and enforce no-show policies —
  registration is a C−7d milestone with real money attached.
- Camera-ready deadlines are often unpublished at planning time (profiles
  carry `camera_ready: null`); the acceptance notification email is the
  authoritative source — re-run the script with `--camera-ready` once
  known.
