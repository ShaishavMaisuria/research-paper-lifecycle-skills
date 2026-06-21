# The IEEE camera-ready rail: PDF eXpress → file naming → eCF → registration

Detailed walkthrough for venues with `camera_ready.rail: ieee-pdfexpress`
(ICDE, ICDM, IEEE BigData, ICDCS, IPDPS, and most IEEE / IEEE Computer
Society conferences published in IEEE Xplore). Facts below match the
verified family profile `venues/families/ieee-conf.yml`; the camera-ready
instructions in the acceptance email ALWAYS win — IEEE venues vary more
than ACM ones in where final files are collected.

## Table of contents

1. [The pipeline at a glance](#1-the-pipeline-at-a-glance)
2. [Step 1 — Get the PDF eXpress Conference ID](#2-step-1--get-the-pdf-express-conference-id)
3. [Step 2 — Final IEEEtran formatting](#3-step-2--final-ieeetran-formatting)
4. [Step 3 — Validate with PDF eXpress](#4-step-3--validate-with-pdf-express)
5. [Step 4 — File naming conventions](#5-step-4--file-naming-conventions)
6. [Step 5 — Upload to the right collection site](#6-step-5--upload-to-the-right-collection-site)
7. [Step 6 — The eCF copyright form](#7-step-6--the-ecf-copyright-form)
8. [Step 7 — Registration and the no-show policy](#8-step-7--registration-and-the-no-show-policy)
9. [Lead times](#9-lead-times)
10. [Common failure modes](#10-common-failure-modes)

## 1. The pipeline at a glance

```
acceptance email (contains the PDF eXpress Conference ID + instructions)
   └─> final IEEEtran formatting (de-anonymize, strip page numbers,
       add copyright notice if required)
          └─> PDF eXpress: create title, validate PDF (or convert source)
                 └─> "passed" certificate email
                        └─> rename certified PDF per venue convention
                               └─> upload to the DESIGNATED collection site
                                      └─> complete the IEEE eCF (one shot!)
                                             └─> register + present (no-show
                                                 = pulled from Xplore)
```

Order matters less than on the ACM rail (eCF and upload are sometimes
swapped), but validation must precede upload, and everything must be done
by the camera-ready AND registration deadlines.

## 2. Step 1 — Get the PDF eXpress Conference ID

- Every IEEE conference gets a per-event **Conference ID** for PDF eXpress,
  shaped like `61234X` (digits + letter). It is printed in the acceptance
  email or the camera-ready instructions page.
- Without it you cannot enroll the paper — PDF eXpress accounts are scoped
  per conference, so even returning users must "add" the new Conference ID.
- If the ID is missing from the email, check the venue's "Camera-ready /
  Final submission" page, then ask the publication chair. Never guess or
  reuse last year's ID.

## 3. Step 2 — Final IEEEtran formatting

- Class: `\documentclass[conference]{IEEEtran}` (10pt Times, two-column,
  US Letter default). If the venue shipped a modified class, use theirs.
- **De-anonymize** if the venue reviewed blind (restore authors with
  `\IEEEauthorblockN`/`\IEEEauthorblockA`, acknowledgments, real links) —
  see `references/deanonymize-and-extra-pages.md`. Many IEEE venues are
  single-blind; then there is nothing to restore.
- **No page numbers, headers, or footers** — Xplore stamps its own. Remove
  `\pagestyle{...}`, `\pagenumbering{...}`, `\setcounter{page}{...}`, and
  any line numbers left from review.
- **Copyright notice on page 1**: many IEEE conferences require a footer
  like `979-8-3315-XXXX-X/26/$31.00 ©2026 IEEE` on the first page
  (`\IEEEoverridecommandlockouts` + `\IEEEpubid{...}`). The exact string
  (ISBN, price, copyright line variant for US-government/Crown authors) is
  venue-specific — copy it from the camera-ready instructions, never
  fabricate it. Some venues instead stamp it during production; follow the
  instructions.
- Respect the final page limit and any paid overlength allowance (see the
  +page rules reference). Mandatory sections stay (e.g. ICDE 2026's
  AI-Generated Content Acknowledgement before References).

## 4. Step 3 — Validate with PDF eXpress

- Site: `https://ieee-pdf-express.org/` — create an account (or add this
  Conference ID to an existing one), then create a **title record** for the
  paper.
- Two modes:
  - **Check**: upload your compiled PDF; it is verified against IEEE Xplore
    compatibility rules.
  - **Convert**: upload a source zip; PDF eXpress builds a compliant PDF
    for you (slower; useful when font embedding fights back).
- Iterate until you receive the **"passed" certificate email**; that
  certified PDF (often stamped "Certified by IEEE PDF eXpress") is the file
  you submit. Venues check for the certification — an un-validated PDF is
  rejected even if it "looks fine".
- The most common failure is **fonts not embedded** (Type 3 bitmap fonts,
  figures with non-embedded fonts). Fixes: compile with `pdflatex` using
  Type 1 fonts, re-export figures with fonts embedded or outlined, or use
  the Convert mode.
- Validation limits exist (a fixed number of checks per paper); do not
  burn attempts before the source is final.

## 5. Step 4 — File naming conventions

- Conferences impose exact file names so production can match PDFs to
  metadata. Common pattern at CMT-based venues: `PID<paper-number>.pdf`
  (the PID from the submission system), e.g. `PID1234567.pdf`.
- Other venues want `<lastname>-<paperid>.pdf` or a name issued by the
  collection portal. The convention is in the camera-ready email — follow
  it byte-for-byte; misnamed files are silently dropped or rejected.

## 6. Step 5 — Upload to the right collection site

- IEEE venues split production across systems: **IEEE CPS author portal**
  (ICDE and other CPS-produced proceedings), **CyberChair** (IEEE BigData),
  EDAS, or sometimes the original CMT instance. The acceptance email names
  the one true site.
- It is frequently **NOT the review system** — ICDE 2026 verbatim: do
  **not** upload camera-ready papers or copyright forms to CMT.
- Upload the PDF-eXpress-certified PDF (plus source files if the portal
  asks) and keep the confirmation email/receipt.

## 7. Step 6 — The eCF copyright form

- The **IEEE electronic Copyright Form** is completed by ONE author (the
  corresponding author) through a link issued by the collection portal /
  publication chair.
- **The title and author list on the eCF must EXACTLY match the final
  PDF** — same title wording and capitalization conventions, same authors,
  same order. A mismatch creates an Xplore metadata conflict that chairs
  must untangle manually.
- **The form cannot be redone after submission.** Settle the final title
  and author list before anyone clicks. If a genuine error slips through,
  only the publication chair / IEEE support can reset it.
- An **incomplete eCF blocks IEEE Xplore indexing** — the paper can be
  presented yet never appear in Xplore. Treat the eCF confirmation email as
  a deliverable.
- Special cases (US government employees, Crown copyright) select different
  form variants — the form walks through it; do not improvise.

## 8. Step 7 — Registration and the no-show policy

- **At least one author must register**, almost always at the **full
  (member/non-member) rate** — student registrations usually do NOT cover a
  paper. One full registration often covers a limited number of papers
  (1–2); check the venue's registration page.
- Registration commonly has its own deadline tied to the camera-ready
  deadline, and the camera-ready upload form may demand the registration
  confirmation number — register first.
- **No-show policy**: IEEE reserves the right to exclude papers not
  presented at the conference from IEEE Xplore. Some venues (ICDE 2026:
  in-person presentation mandatory) tighten this further. If the presenting
  author may not get a visa, arrange a substitute presenter with the chairs
  in advance.

## 9. Lead times

| Segment | Typical time |
|---|---|
| Acceptance → camera-ready deadline | 2–4 weeks (hard) |
| PDF eXpress account + first validation | < 1 day |
| Font-embedding fix iterations | hours–days (figures are the time sink) |
| eCF | minutes — but settle title/authors first |
| Registration processing | immediate–days (needed for upload at some venues) |

## 10. Common failure modes

| Symptom | Cause / fix |
|---|---|
| PDF eXpress "fonts not embedded" | Type 3 / figure fonts — embed or outline fonts, or use Convert mode |
| Cannot enroll paper | Wrong/last year's Conference ID — get this year's from the acceptance email |
| Camera-ready "not received" | Uploaded to the review system instead of the designated portal, or misnamed file |
| Paper missing from Xplore months later | Incomplete eCF, or no-show exclusion |
| eCF title mismatch flagged | Title edited after the form — contact the publication chair; the form cannot be redone by authors |
| Copyright notice wrong/missing on page 1 | Used a fabricated or stale ISBN/price string — copy the exact string from THIS year's instructions |

Last verified against live venue pages: 2026-06-11 (see the `verified:`
block in `venues/families/ieee-conf.yml`). Re-verify the Conference ID,
deadlines, fees, and the collection site before the user acts.
