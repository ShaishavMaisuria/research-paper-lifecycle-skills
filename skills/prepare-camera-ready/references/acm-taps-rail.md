# The ACM camera-ready rail: eRights → ORCID → rights/DOI block → TAPS

Detailed walkthrough for venues with `camera_ready.rail: acm-taps`
(SIGSPATIAL, SIGMOD, KDD, WWW, CHI, DEBS, CIKM, most SIG proceedings, and
ACM journals/TOSEM-style Transactions). Facts below match the verified
family profiles `venues/families/acm-sigconf.yml`,
`venues/families/acm-manuscript-chi.yml`, and
`venues/families/acm-journal.yml`; per-venue instructions in the acceptance
email ALWAYS win.

## Table of contents

1. [The pipeline at a glance](#1-the-pipeline-at-a-glance)
2. [Step 1 — The eRights email](#2-step-1--the-erights-email)
3. [Step 2 — ORCID iDs for ALL authors](#3-step-2--orcid-ids-for-all-authors)
4. [Step 3 — Completing the rights form](#4-step-3--completing-the-rights-form)
5. [Step 4 — The rights/DOI block in your paper](#5-step-4--the-rightsdoi-block-in-your-paper)
6. [Step 5 — Preparing the source for TAPS](#6-step-5--preparing-the-source-for-taps)
7. [Step 6 — Uploading to TAPS](#7-step-6--uploading-to-taps)
8. [Step 7 — Proofs: PDF and HTML5](#8-step-7--proofs-pdf-and-html5)
9. [Lead times](#9-lead-times)
10. [Common failure modes](#10-common-failure-modes)

## 1. The pipeline at a glance

```
acceptance email
   └─> eRights email from rightsreview@acm.org   (corresponding author)
          └─> ORCIDs collected for ALL authors
                 └─> rights form completed (exact final title + author list)
                        └─> form returns the rights/DOI block -> paste into preamble
                               └─> TAPS email with submission ID + unique upload link
                                      └─> upload ONE zip of ALL SOURCE files
                                             └─> PDF + HTML5 proofs (~24h)
                                                    └─> approve in TAPS before the deadline
```

Nothing downstream unlocks until the rights form is done — TAPS will not
even contact you. The DOI exists only after the form is processed.

## 2. Step 1 — The eRights email

- Sent by **rightsreview@acm.org** to the **corresponding author only**,
  usually days to a couple of weeks after acceptance (proceedings chairs
  batch-load metadata first).
- It routinely lands in **spam**; have the user search for
  `from:rightsreview@acm.org` before assuming it has not arrived.
- If it has not arrived ~2 weeks after acceptance (or the camera-ready
  deadline is < 1 week away), email the proceedings/publication chair —
  authors cannot trigger the form themselves.
- The email links to the ACM eRights form for THIS paper. Do not forward it
  casually: whoever opens it acts as the corresponding author of record.

## 3. Step 2 — ORCID iDs for ALL authors

- ACM requires an **ORCID iD for every author** — not just the submitter —
  before the rights form can be completed.
- Registration is free at `https://orcid.org` and takes ~2 minutes per
  author. Collect them BEFORE opening the form; chasing a coauthor across
  time zones is the classic last-minute blocker.
- Authors should claim/verify their own iDs (an ORCID identifies a person;
  do not register one on a coauthor's behalf).
- Put the iDs into the source too where the class supports it
  (`\orcid{0000-...}` in acmart) — ACM links them in the DL.

## 4. Step 3 — Completing the rights form

- The form must carry the **EXACT final title and the exact author list and
  order** of the camera-ready paper. The rights-form metadata is
  authoritative: in TAPS it **overrides whatever is in your source files**.
  Fix discrepancies in the form (or via the publication chair), not by
  editing the .tex and hoping.
- Author changes after submission are restricted at most venues (NeurIPS
  bans add/remove outright; ACM venues route changes through the chairs).
  Settle the author list before the form, not after.
- The form offers rights options — typically copyright transfer, exclusive
  licence, or (paid / default at some SIGs) Open Access. This is the
  authors'/institution's decision; explain options, never choose for them.
  Some venues note fee waivers (e.g. SIGSPATIAL short papers converted to
  posters avoid the OA fee) — check the venue page.

## 5. Step 4 — The rights/DOI block in your paper

Completing the form generates LaTeX commands (Word authors get a text
strip) that MUST be inserted into the camera-ready source — papers without
them bounce in production. Typical block, before `\begin{document}`:

```latex
\setcopyright{acmlicensed}
\acmConference[SIGSPATIAL '26]{34th ACM SIGSPATIAL International
  Conference on Advances in Geographic Information Systems}{November
  3--6, 2026}{Riverside, CA, USA}
\acmBooktitle{...}   % when provided
\acmYear{2026}
\acmISBN{979-8-4007-XXXX-X/26/11}   % YOUR value from the form
\acmDOI{10.1145/XXXXXXX.XXXXXXX}    % YOUR value from the form
\acmPrice{15.00}                    % if provided
```

- Copy the values **verbatim from the confirmation email/form output**.
  Never leave the acmart sample placeholders (`10.1145/nnnnnnn.nnnnnnn`,
  `978-x-xxxx-xxxx-x/YY/MM`) — `scripts/check_camera_ready.py` flags them.
- Journals get `\acmJournal`/volume/number commands instead of
  `\acmConference`.

## 6. Step 5 — Preparing the source for TAPS

TAPS compiles your **source** (LaTeX or Word) into the published two-column
PDF and HTML5 — you cannot upload "just the PDF".

- Switch to the camera-ready class: drop `review` and `anonymous`
  (`\documentclass[sigconf]{acmart}`; CHI authors switch from
  `manuscript` to `sigconf`; some venues add options like `9pt` — check the
  venue page). Restore authors, affiliations, emails, ORCIDs.
- Restore acknowledgments and funding (`\begin{acks}...\end{acks}` — TAPS
  styles it correctly and grant agencies require it).
- **CCS concepts and keywords are mandatory**: generate the CCSXML block and
  `\ccsdesc` commands at `https://dl.acm.org/ccs`, add free-text
  `\keywords{...}`, and confirm the ACM Reference Format block renders on
  page 1 (acmart auto-generates it).
- **Package whitelist**: TAPS accepts only an approved list of LaTeX
  packages
  (https://authors.acm.org/proceedings/production-information/accepted-latex-packages).
  Replace unsupported packages now — TAPS rejections cost a day each.
- Compile cleanly against the **current acmart release**; stale local copies
  of acmart.cls cause TAPS mismatches.
- Figures: include every file the source references; provide meaningful
  **alt text** (`\Description{...}`) — required for accessibility at CHI
  and increasingly enforced family-wide.

## 7. Step 6 — Uploading to TAPS

- After the rights form is processed, **TAPS emails a submission ID and a
  unique upload link** for the paper.
- Upload **ONE zip containing ALL source files** — `.tex`, `.bib`, custom
  `.sty`/`.cls`, every figure — named exactly as the email instructs
  (typically `<ProceedingsAcronym>-<PaperID>.zip`). Wrong name or partial
  zip = automatic bounce.
- After the first upload, make corrections **inside TAPS** by revising the
  uploaded files there; some workflows (journals especially) do not accept
  re-uploads of fresh local zips.

## 8. Step 7 — Proofs: PDF and HTML5

- Within ~24 hours TAPS emails "PDF and HTML Proofs: available for review".
- Check **both** renderings — HTML5 breaks differently (math, tables,
  figure alt text, special characters in author names).
- Approve in TAPS, or reject with fixes and re-check, before the
  camera-ready deadline. Unapproved papers miss the proceedings cut.

## 9. Lead times

| Segment | Typical time |
|---|---|
| Acceptance → eRights email | days to ~2 weeks |
| Collecting ORCIDs from all coauthors | minutes to days (time zones) |
| Rights form processed → TAPS upload link | hours to days |
| TAPS compile/proofs per iteration | ~24 h |
| Whole rail, end to end | **often 1–3 weeks — start the day acceptance arrives** |

## 10. Common failure modes

| Symptom | Cause / fix |
|---|---|
| "No eRights email" | Spam folder; or proceedings chair has not loaded metadata — email the publication chair, never wait silently past 2 weeks |
| Form rejects completion | A coauthor has no ORCID — collect all iDs first |
| TAPS shows wrong title/authors | Rights-form metadata overrides source — correct via the form/publication chair |
| TAPS compile fails | Unsupported package (check the whitelist), missing figure/bib file in the zip, stale acmart |
| Paper bounces with "missing rights block" | Rights/DOI commands absent or still sample placeholders — paste YOUR values |
| Proofs look wrong only in HTML | Math/table constructs that acmart's HTML path dislikes — simplify or ask TAPS support |
| Venue not on TAPS at all | Some conferences leave TAPS (e.g. FAccT) — ALWAYS follow the acceptance email over this guide |

Last verified against live venue pages: 2026-06-11 (see the `verified:`
blocks in `venues/families/acm-*.yml`). Re-verify before relying on any
date, fee, or URL.
