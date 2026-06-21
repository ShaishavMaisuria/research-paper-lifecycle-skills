# Templates, Submission Systems, Rebuttal Formats, Camera-Ready Rails

Lookup tables for normalizing CFP facts into schema fields. Everything here is
a *prior*, not ground truth — the live CFP always wins when it states otherwise.

## Table of contents

1. [Template invocation by family](#1-template-invocation-by-family)
2. [Submission-system detection](#2-submission-system-detection)
3. [Rebuttal format taxonomy](#3-rebuttal-format-taxonomy)
4. [Camera-ready rails](#4-camera-ready-rails)
5. [Required-section extras by venue family](#5-required-section-extras-by-venue-family)

## 1. Template invocation by family

| Family | `format.template` | Submission invocation | Camera-ready invocation |
|---|---|---|---|
| acm-sigconf (SIGSPATIAL, SIGMOD, KDD, CCS...) | `acmart` | double-blind: `\documentclass[sigconf,review,anonymous]{acmart}` · single-blind: `\documentclass[sigconf,review]{acmart}` | `\documentclass[sigconf]{acmart}` |
| acm-manuscript-chi (CHI, CSCW, UIST) | `acmart` | `\documentclass[manuscript,review,anonymous]{acmart}` (1-column; TAPS produces 2-column later) | via TAPS |
| ieee-conf (ICDE, ICDM, generic IEEE) | `IEEEtran` | `\documentclass[conference]{IEEEtran}` (blinding by omitting authors — no `anonymous` option exists) | same |
| neurips-style (NeurIPS, ICML, ICLR) | `neurips` | `\documentclass{article}` + `\usepackage{neurips_<YEAR>}` (ICML: `icml<YEAR>.sty`; ICLR: `iclr<YEAR>_conference.sty`) — capture the exact year-versioned file the CFP names | same with `final` option |
| lncs (Springer conferences) | `llncs` | `\documentclass{llncs}` | same; Springer license form |
| aaai-style (AAAI, AIES) — no `venues/families/aaai.yml` exists; profiles set the closest family, `neurips-style` (per-year style file) | `aaai` | AAAI-<YEAR> author kit, two-column (`aaai<YY>.sty`) | same |
| ieee-journal (TKDE...) | `IEEEtran` | `\documentclass[journal]{IEEEtran}` | same |
| acm-journal (TODS, PACMMOD...) | `acmart` | `\documentclass[manuscript,review,anonymous]{acmart}` | `\documentclass[acmsmall]{acmart}` (journal-specific) |

Rules of thumb:

- Add `review` (line numbers) and `anonymous` options **only** for double/triple-blind
  ACM venues; SIGSPATIAL is single-blind so its profile must NOT carry `anonymous`.
- ML venues version their style file every year — `neurips_2026.sty` is a
  different file from `neurips_2025.sty` and venues desk-reject the wrong one.
  Always record the year the CFP names.
- Template tampering (margins, spacing, font hacks) is an explicit desk-reject
  trigger at SIGSPATIAL, Springer, NeurIPS and most ACM venues — when the CFP
  says so, copy the warning into the track `notes`.

## 2. Submission-system detection

Detect from URLs on the CFP page (the fetch script prints link targets as `[url]`):

| URL pattern | `submission_system` |
|---|---|
| `openreview.net/group?id=...` | `openreview` |
| `cmt3.research.microsoft.com/...` | `cmt` |
| `easychair.org/conferences/?conf=...` | `easychair` |
| `*.hotcrp.com` or `/hotcrp/` | `hotcrp` |
| `precisionconference.com` / `new.precisionconference.com` | `pcs` |
| `mc.manuscriptcentral.com/...` | `scholarone` (journals) |

Venue priors (hints only — confirm against the live page):

- **OpenReview**: NeurIPS, ICML, ICLR (public reviews at ICLR).
- **CMT**: ICDE and many IEEE conferences.
- **EasyChair**: SIGSPATIAL and a huge long tail; each track may have its OWN
  conference code — record every code in the track notes.
- **HotCRP**: USENIX venues, SIGCOMM, SIGPLAN, SOSP, security conferences.
- **PCS**: CHI, UIST, CSCW (SIGCHI family), IEEE VIS.

## 3. Rebuttal format taxonomy

| `rebuttal_format` | What it means | Real examples |
|---|---|---|
| `none` | No author response phase | SIGSPATIAL 2026 |
| `openreview-thread` | Per-review threaded text responses with a character budget | NeurIPS: 10,000 chars per review, 3 phases (response, rolling discussion, reviewer-AC only) |
| `one-page-pdf` | Strict single-page PDF on the official rebuttal template; overruns are not read | CVPR (`rebuttal.tex` in the author kit) |
| `revise-and-resubmit` | Weeks-long revision with tracked changes + response document | CHI (R&R window, ~4 weeks in the 2026 cycle), SIGMOD/ICDE revision rounds, journals |

Put the exact budget in `rebuttal_limit` ("10000 chars per review", "1 page
PDF", "5 weeks, tracked changes + response doc").

## 4. Camera-ready rails

| `rail` | Steps the profile's `requirements` should reflect |
|---|---|
| `acm-taps` | eRights form email (rightsreview@acm.org) → ORCID iDs for ALL authors → insert returned rights/DOI block → upload LaTeX/Word SOURCE to TAPS → approve proof. Takes weeks; start early. |
| `ieee-pdfexpress` | Format in IEEEtran → validate/convert via IEEE PDF eXpress with the conference ID → rename per convention (e.g. `PIDxxx`) → upload certified PDF → complete IEEE eCF (title/authors must match the PDF exactly; cannot be redone) → register + present (no-show policy). |
| `springer` | Final llncs source + figures → signed Springer licence-to-publish → corresponding-author details; keep LNCS format untouched. |
| `openreview-direct` | Final PDF with year's style file in `final` mode (+1 content page at NeurIPS) → de-anonymize, restore acknowledgments → upload to OpenReview; code links allowed post-acceptance. |

Venues migrate rails (FAccT 2026 left TAPS) — re-check the venue's own
camera-ready page every cycle.

## 5. Required-section extras by venue family

Desk-reject-grade extras to put in `format.required_sections` when applicable:

- **neurips-style**: `neurips-checklist` (missing checklist = desk reject; the
  checklist pages do not count toward the limit); ICML adds
  `icml-impact-statement`.
- **ieee-conf (ICDE)**: `ai-use-acknowledgement` (mandatory section naming the
  AI system and affected sections) and `coi-declaration` (missing COI = desk
  reject).
- **acm-sigconf / acm-manuscript-chi**: `ccs-concepts`, `keywords`,
  `acm-reference-format`.
- **lncs**: 150–250 word abstract, 3–6 keywords, ORCID in the title block.
