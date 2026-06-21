# Submission Systems — per-system steps and gotchas

Reference for the `plan-submission` skill. Covers the five systems that
run essentially all CS-conference submissions: OpenReview, Microsoft CMT,
EasyChair, HotCRP, and PCS. The venue profile's
`review.submission_system` + `submission_url` say which one applies.

Interfaces and policies drift — treat this file as orientation and
re-verify lead times and form fields on the venue's own author
instructions before the user depends on them. Never operate any of these
systems on the user's behalf.

## Table of contents

1. [System → venue map and URL fingerprints](#1-system--venue-map-and-url-fingerprints)
2. [OpenReview](#2-openreview)
3. [Microsoft CMT](#3-microsoft-cmt)
4. [EasyChair](#4-easychair)
5. [HotCRP](#5-hotcrp)
6. [PCS (Precision Conference Solutions)](#6-pcs-precision-conference-solutions)
7. [Day-before checklist (any system)](#7-day-before-checklist-any-system)

## 1. System → venue map and URL fingerprints

| System | Typical venues | URL looks like |
|---|---|---|
| OpenReview | NeurIPS, ICML, ICLR, many ML workshops | `openreview.net/group?id=Venue/Year/Conference` |
| Microsoft CMT | ICDE, ICME, many IEEE conferences | `cmt3.research.microsoft.com/<Venue><Year>` |
| EasyChair | SIGSPATIAL, EDBT, huge long tail of conferences/workshops | `easychair.org/conferences/?conf=...` |
| HotCRP | USENIX venues, SIGCOMM, SOSP, SIGPLAN, security conferences | `<venue><yy>.hotcrp.com` or self-hosted |
| PCS | CHI, UIST, CSCW, SIGCHI family, IEEE VIS | `new.precisionconference.com` |

ACM provides hosted EasyChair/HotCRP licenses, so ACM venues appear on
several systems — trust the profile/CFP, not the publisher.

## 2. OpenReview

**Account lead time: the long pole — plan 2 weeks.**

- New profiles registered with **non-institutional emails go through
  moderation that can take up to ~2 weeks**; institutional-email signups
  activate much faster. Every author should register with an
  institutional email at T-14d or earlier.
- Major venues require a **complete profile for every author** at
  submission time: current + past affiliations (with years), DBLP profile
  import of publications, advisor/co-author relations, and email domains.
  Conflicts are computed automatically from profile domains and co-author
  history — an empty co-author profile silently breaks conflict detection
  and can violate venue rules.
- Submission form: title, abstract, author list (each author selected by
  OpenReview profile, not typed), subject areas, conflicts, PDF upload,
  separate supplementary upload (ZIP; venue-specific size cap), plus
  venue-specific declarations (LLM-use, ethics, reproducibility
  checklist confirmations).
- Edits: submissions are usually editable until the deadline; some venues
  open a short post-deadline edit window for the PDF only — check the
  venue's dates page, never assume.
- Abstract registration happens in the same form: create the submission
  record with title/abstract/authors by the abstract deadline, attach or
  replace the PDF by the paper deadline.
- Rebuttals later happen here too, as per-review threaded replies with
  character limits (profile `rebuttal_limit`).
- Gotcha: the author list at many OpenReview venues becomes immutable at
  the abstract or paper deadline — typo'd or missing co-author profiles
  are unfixable afterwards.

## 3. Microsoft CMT

**Account lead time: instant, but COI entry is the real task.**

- Accounts at `cmt3.research.microsoft.com` are self-serve and instant.
  Each conference is a separate site under the same login; authors must
  be added by the **exact email** their CMT account uses, or the paper
  will not appear in their author console.
- Conflict-of-interest entry is manual and venue-policied: mark conflict
  domains and individual PC conflicts. IEEE data venues (ICDE-style)
  publish detailed COI definitions (co-authorship in the past 3 years,
  4+ co-authorships in 10 years, same institution within 3 years,
  advisor/advisee ever, relatives/close friends) and **desk-reject for
  missing COI declarations** — budget real time for this per author.
- Submission form: track selection first (irreversible at some venues),
  title/abstract, authors, subject areas (drive reviewer assignment),
  PDF upload, venue-specific questions (ORCID per author at ICDE,
  AI-generated-content acknowledgement, artifact intentions).
- Edits: typically allowed until the deadline; the "Edit Submission"
  path re-validates required fields — a late edit can un-submit a paper
  if a newly-required field is blank, so re-check status after any edit.
- Camera-ready later: IEEE venues on CMT route the IEEE eCF (copyright)
  through a CMT link, and file naming follows the paper ID (e.g.
  `PID<paper-number>`).

## 4. EasyChair

**Account lead time: instant. Risk concentrates in manual data entry.**

- Accounts are instant and global; a conference link
  (`easychair.org/conferences/?conf=...`) adds the author role.
- Author entries are **typed by hand** — name, email, affiliation,
  country, corresponding flag — for every author. A typo'd co-author
  email orphans the paper from that author's account and corrupts the
  proceedings metadata. Copy emails from the frozen author list (T-10d
  milestone), never from memory.
- Abstract registration pattern (SIGSPATIAL-style): submit the form with
  title + abstract + authors + keywords by the abstract deadline, then
  use "Update file" to attach/replace the PDF until the paper deadline.
  Record the submission number from the confirmation email.
- Multi-track installations list all tracks in one place — submitting to
  the wrong track (Research vs Demo vs Industrial) is easy and at some
  venues unrecoverable; confirm the track name on the submission page
  header before uploading.
- Title conventions live OUTSIDE the system: e.g. SIGSPATIAL experiment
  papers must carry a title suffix per the CFP — EasyChair will not
  validate it; the preflight must.
- Edits: allowed until the deadline via "Update information / file /
  authors"; after the deadline the chairs control everything.

## 5. HotCRP

**Account lead time: instant. The signature gotcha is the ready checkbox.**

- Accounts are created on first visit (per-installation, e.g.
  `<venue>.hotcrp.com`); co-authors are added by email and get accounts
  automatically.
- **"The submission is ready for review" checkbox**: HotCRP
  distinguishes *draft* (saved, NOT considered submitted at most venues)
  from *ready*. Papers left in draft state at the deadline are not
  reviewed. Verify the status banner says the paper is submitted/ready
  — this single checkbox is the most common HotCRP failure.
- Form: title, abstract, authors, **topics** (reviewer matching),
  collaborators/conflicts (institutional + recent co-authors, used to
  exclude reviewers), PDF upload. Some installations run an automatic
  format checker (page count, font size, margins) at upload — treat its
  warnings as desk-reject predictors, not suggestions.
- Anonymity: HotCRP venues (systems/security) are commonly double-blind
  with strict rules; the conflicts field replaces author-visible
  identity, so fill it exhaustively.
- Edits: uploads can be replaced until the deadline; many venues allow
  un-finalizing before the deadline but nothing after.

## 6. PCS (Precision Conference Solutions)

**Account lead time: instant, but metadata locks EARLY.**

- One account at `new.precisionconference.com` covers all societies;
  pick society → venue → track from dropdowns to start a submission.
- **Metadata lock**: at CHI-style venues the title, abstract, author
  list, and subcommittee selection are due at the *metadata/abstract
  deadline* (about a week before the PDF) and are locked afterwards.
  The PDF and supplementary upload slots stay open until the paper
  deadline.
- Subcommittee choice (CHI) is strategic, not clerical: it determines
  which 1AC/2AC pool and reviewer culture judges the paper. Decide it
  during the abstract-registration milestone with co-authors, not in the
  form.
- Form: contribution type, subcommittee, authors (typed, with
  affiliations), abstract, keywords/CCS concepts, PDF (single-column
  manuscript format at CHI), supplementary (videos are common and have
  their own size caps), anonymization confirmations.
- Anonymity: SIGCHI venues desk-reject for identity leaks **including in
  supplementary materials and linked repos** — the T-5d supplementary
  milestone matters double here.
- Edits: files replaceable until the paper deadline; metadata is not.

## 7. Day-before checklist (any system)

Run at the T-1d milestone, inside the submission system:

1. Open the actually-uploaded PDF from the system (not the local file) —
   correct version, fonts embedded, all pages present.
2. Form metadata (title, abstract, author order) matches the PDF exactly
   — mismatches trigger desk checks and corrupt proceedings data.
3. Submission status is "complete"/"ready", not "draft" (HotCRP
   especially).
4. Supplementary attached and within the size cap; opens cleanly.
5. Required declarations answered (LLM/AI use, ethics, COI, ORCID).
6. Confirmation email received and archived; submission number recorded.
7. Note the system's clock vs the stated timezone — the form's countdown
   is authoritative.
