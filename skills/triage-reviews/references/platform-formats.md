# Platform formats — getting clean review text out of each system

What raw reviews look like on OpenReview, EasyChair, CMT, and HotCRP, how to
copy them out cleanly for `parse_reviews.py`, and what the score scales mean.
Platform UIs churn; when the paste looks different from the descriptions
below, fall back to manual reviewer splitting (see last section).

## Contents

- [OpenReview](#openreview)
- [EasyChair](#easychair)
- [Microsoft CMT](#microsoft-cmt)
- [HotCRP](#hotcrp)
- [PCS and ScholarOne (journals)](#pcs-and-scholarone-journals)
- [Score-scale cheat sheet](#score-scale-cheat-sheet)
- [When auto-parsing fails](#when-auto-parsing-fails)

## OpenReview

Used by NeurIPS, ICML, ICLR, and increasingly CVPR/ECCV-family venues.

- **Copy-out**: open the paper's forum page, expand every "Official Review"
  note, select-all and paste. Each review starts with a line like
  `Official Review of Submission4127 by Reviewer Xk2P` — keep those lines;
  the parser splits on them. Anonymous reviewer ids are 4 alphanumeric
  characters.
- **Structured fields** (venue-configured, NeurIPS-style): `Summary`,
  `Strengths`, `Weaknesses`, `Questions`, `Limitations`, plus scored fields
  `Soundness` / `Presentation` / `Contribution` (1-4), `Rating` (1-10 with
  text, e.g. `6: marginally above the acceptance threshold`), `Confidence`
  (1-5). ICLR adds public comments; treat non-reviewer comments as context,
  not concerns — delete them from the paste or remove them from the JSON.
- **Rebuttal mechanics to mine the venue profile for**: NeurIPS-style
  venues cap each per-review response (10,000 characters at NeurIPS,
  5,000 at some others), allow markdown, forbid links to non-anonymized
  artifacts, and run a multi-phase discussion after the initial response.
- **Gotcha**: the UI sometimes renders rating fields twice (header + body);
  the parser keeps the last occurrence per field — harmless, but check.

## EasyChair

Used by SIGSPATIAL and a very long tail of conferences and workshops.

- **Copy-out**: easiest source is the notification email or the "Reviews"
  page. The export banner per review is
  `----------------------- REVIEW 1 ---------------------` followed by
  `PAPER:`/`TITLE:`/`AUTHORS:` metadata echoes (the parser drops these).
- **Fields**: `OVERALL EVALUATION: <n> (<label>)` and
  `REVIEWER'S CONFIDENCE: <n> (<label>)`, then a free-text
  `----------- Overall evaluation -----------` body. Numeric scale is
  venue-configured, commonly -3..+3 or -2..+2 (negative = reject side).
  There are usually NO structured weakness sections — concerns are
  paragraphs or numbered lists inside the body, which is exactly what the
  parser's paragraph/list splitter handles.
- **Gotcha**: sub-reviewer sign-offs ("Reviewed by: ...") and confidential
  remarks to the PC are sometimes pasted accidentally; remove anything not
  addressed to the authors before triage.

## Microsoft CMT

Used by ICDE, ICME, and many IEEE-family conferences
(cmt3.research.microsoft.com).

- **Copy-out**: the author console shows reviews behind "View Reviews";
  each starts with `Reviewer #1` / `Reviewer #2`. CMT review forms are
  fully venue-configured — questions appear as numbered prompts
  (`Q1. Summary`, `Q2. Strengths`, ...) or as bold headings.
- **Parsing reality**: because forms vary per venue, auto-section mapping
  is weakest on CMT. Expect more text to land in `comments`/`other`; the
  concern items themselves still split fine. Re-map `source_section` by
  hand in the JSON when it matters.
- **Meta-reviews**: CMT venues often include a `Meta-Reviewer` block —
  the parser tags it `role: meta`; its concerns outrank same-severity
  reviewer concerns (see triage-rubric.md).

## HotCRP

Used by USENIX, SIGCOMM, SOSP/OSDI, SIGPLAN, and most security venues.

- **Copy-out**: reviews page or notification email. Header per review is
  `Review #87A`, `Review #87B`, ... (paper number + reviewer letter).
- **Fields**: `Overall merit` and `Reviewer expertise` as `n. label`
  (typically 1-5: reject ... strong accept), then prose sections
  `Paper summary` and `Comments for authors` underlined with dashes (the
  parser strips the underline rows). Some venues add `Questions for
  authors' response` — exactly the items the rebuttal must answer; they
  parse into `questions`.
- **Gotcha**: HotCRP text exports hard-wrap at ~75 columns; the parser
  joins wrapped lines within a paragraph, but check that no concern got
  split mid-sentence.

## PCS and ScholarOne (journals)

- **PCS** (CHI/UIST/CSCW): reviews arrive as 1AC/2AC meta-reviews plus
  external reviews, usually pasted from email. There are no reliable
  banners — insert `Review 1`, `Review 2`, `Meta-Review` lines by hand
  before parsing. The CHI Revise-and-Resubmit response is a document, not
  a thread; triage still applies, the budget does not.
- **ScholarOne / journal R&R** (TKDE, TODS): reviewer comments come as
  "Reviewer: 1 / Comments to the Author" blocks. Replace those headers
  with `Reviewer #1` lines and parse with `--format cmt`. Journal
  responses are unbounded documents — skip `--budget` and prioritize by
  band only.

## Score-scale cheat sheet

| Platform / venue style | Overall field | Scale | Reject↔accept midpoint |
|---|---|---|---|
| OpenReview (NeurIPS-style) | `Rating` | 1-10 | 5/6 boundary ("marginally below/above") |
| OpenReview aux | `Soundness`/`Presentation`/`Contribution` | 1-4 | 2/3 |
| OpenReview / all | `Confidence` | 1-5 | n/a (weight, not valence) |
| EasyChair | `OVERALL EVALUATION` | -3..+3 or -2..+2 | 0 |
| HotCRP | `Overall merit` | 1-5 (sometimes 1-4) | 2/3 |
| CMT | venue-configured | varies | read the label text, not the number |

Always read the label text shipped with the number — scales differ even
between years of the same venue. Record each reviewer's valence
(positive / borderline / negative) before classifying concerns; it drives
severity calibration (triage-rubric.md, "Reviewer-leverage heuristics").

## When auto-parsing fails

1. Re-run with an explicit `--format openreview|easychair|cmt|hotcrp`.
2. Lower the threshold: `--min-words 3` (catches terse one-line concerns).
3. Insert manual banners: a standalone line `Review 1` / `Reviewer #2` /
   `Meta-Review` before each review in the text file is enough for the
   generic splitter.
4. As a last resort, edit the JSON skeleton directly — add missed concerns
   with the next free id and set `source_section` to where they came from.
   Never silently drop a reviewer point: every concern in the raw text must
   appear in the matrix, even if classified `minor`/`brief`.
