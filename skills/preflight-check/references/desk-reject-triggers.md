# Desk-Reject Triggers — the evidence behind each check

Verified against live CFPs in June 2026. Venue rules churn every year:
**always re-verify against the profile's `cfp_url` before relying on any
number on this page.**

## Contents

- [1. Page-limit violations](#1-page-limit-violations)
- [2. Template and margin tampering](#2-template-and-margin-tampering)
- [3. Wrong documentclass / style file](#3-wrong-documentclass--style-file)
- [4. Anonymization leaks (double-blind venues)](#4-anonymization-leaks-double-blind-venues)
- [5. Missing mandatory sections and statements](#5-missing-mandatory-sections-and-statements)
- [6. Abstract and keywords](#6-abstract-and-keywords)
- [7. Triggers outside the linter's reach](#7-triggers-outside-the-linters-reach)

## 1. Page-limit violations

NeurIPS states it plainly: papers violating page limits or style "will not be
reviewed". The trap is that *what counts toward the limit* differs per venue
and per track:

| Venue (cycle) | Limit | Excluded from the count |
|---|---|---|
| NeurIPS 2026 main | 9 content pages (+1 at camera-ready) | references, appendices, mandatory checklist |
| ICML 2026 | 8 pages | references, impact statement, appendices |
| SIGSPATIAL 2026 Research | 10 pages | references, +2 appendix pages after refs |
| SIGSPATIAL 2026 Demo | 4 pages | nothing — references count |
| SIGMOD 2026 | 12 pages | citations (unlimited); appendix = separate PDF |
| ICDE 2026 | 12 pages | references |
| ICDM | 10 pages | nothing — bibliography and appendix count |
| CHI 2026 | no hard limit | length weighed against contribution; ≤5,000-word short papers welcomed |
| LNCS conferences (typical) | 12 pages | often nothing; some allow a 2-page appendix |
| TKDE (journal) | 14 double-column pages | nothing — references and bios count |

Implications for the check:

- `check_template.py` reads the page count from the adjacent `.log`
  (`Output written on ... (N pages`) or, approximately, from the `.pdf`.
  Without a compiled artifact it can only remind the user to count manually.
- When the limit *excludes* matter, total pages > limit is a **WARN**, not an
  ERROR: the linter cannot see on which page the references begin. Have the
  user confirm content ends by the limit page.
- When nothing is excluded (SIGSPATIAL Demo, ICDM, TKDE), total pages > limit
  is an outright **ERROR**.

## 2. Template and margin tampering

SIGSPATIAL, Springer/LNCS, and most ACM venues state that changing margins,
page size, or spacing is grounds for rejection without review. Chairs run
automated format checkers (and reviewers notice cramped pages). The linter
flags, in rough order of how damning they are:

- `\usepackage{geometry}` / `\geometry{...}` / `\newgeometry` — page layout
  override. ERROR.
- `\usepackage{savetrees}` — exists specifically to compress papers. ERROR.
- `\usepackage{fullpage}` — margin override. ERROR.
- `\setlength`/`\addtolength` on `\textwidth`, `\textheight`, `\topmargin`,
  `\oddsidemargin`, `\columnsep`, etc. — ERROR.
- `\linespread{x}` / `\baselinestretch` / `\setstretch` with x < 1 —
  compressed leading. ERROR.
- `\renewcommand{\normalsize}` — body font tampering. ERROR.
- `\setlength` on `\parskip`, float/caption/display skips — WARN (space
  compression; sometimes legitimate).
- Negative `\vspace`/`\vskip` — WARN each; 5+ is flagged as a systematic
  pattern. One or two around figures is normal LaTeX life.
- `\enlargethispage` — WARN.

False-positive note: some templates themselves set lengths (inside `.sty`
files). The linter only scans the user's own sources (`\input`-followed), so
class/style files are not scanned — that is by design.

## 3. Wrong documentclass / style file

Family rules (see `venues/families/`):

- **acmart (ACM sigconf)** — submission at double-blind members:
  `\documentclass[sigconf,review,anonymous]{acmart}` (option order is
  interchangeable). Single-blind members (SIGSPATIAL) drop `anonymous`
  — keeping it there is an ERROR, since the CFP requires author names listed.
  `review` adds line numbers reviewers expect: missing it is a WARN.
  CHI uses `[manuscript,review,anonymous]` (one column).
- **NeurIPS-style (NeurIPS/ICML/ICLR)** — class is plain `article` plus a
  *year-versioned* style file: `neurips_2026.sty`, `icml2026.sty`,
  `iclr2026_conference.sty`. Submitting on last year's file is an explicit
  desk-reject risk (NeurIPS 2026 accepts only `neurips_2026.sty`; Word is no
  longer accepted). `[final]` prints author names — camera-ready only.
  `[preprint]` is for arXiv, not submission.
- **IEEEtran (IEEE conferences)** — `IEEEtran.cls`, two-column, 10pt.
- **llncs (Springer LNCS)** — `llncs.cls`; changing page size/margins is
  prohibited; camera-ready must remain LNCS format.

`check_template.py` compares the found `\documentclass` (and `.sty` for the
NeurIPS family) against `format.documentclass` in the merged profile.

## 4. Anonymization leaks (double-blind venues)

CHI and NeurIPS desk-reject for anonymization violations, *including in
supplementary materials and linked repositories*. What the linter scans:

- **Author block** — populated `\author`, `\affiliation`, `\institute`,
  `\email`, `\orcid`. At NeurIPS-style venues the `.sty` hides the block at
  submission, so it is downgraded to a WARN there (scrub anyway: sources get
  shared); everywhere else it is an ERROR.
- **`\thanks{...}`** — classic leak: funding + affiliation in a footnote.
- **Acknowledgments** — `\begin{acks}`/`\begin{ack}`/acknowledgment sections
  must be absent from a double-blind submission (NeurIPS says explicitly: no
  acknowledgments at submission).
- **Funding lines** — "grant no. ...", "funded by", agency + number.
- **Repository / personal links** — `github.com/<user>/...`, GitLab,
  Hugging Face, Google Drive, personal `~user` pages: ERROR. Anonymized
  mirrors (`anonymous.4open.science`) are recognized as fine. arXiv links get
  a WARN: linking your own preprint de-anonymizes you.
- **First-person self-citations** — CHI's rule: cite your own work in third
  person ("As described by Chetty et al. [10]"), never "our previous work
  [10]". The linter pattern-matches "our previous/prior/earlier work",
  "we previously showed", "builds on our", "our ... \cite", etc. These are
  WARNs — wording, not certainty.
- **PDF metadata** — `pdfauthor={...}` via hyperref lands the author name in
  the compiled PDF's metadata. ERROR. (Metadata set by the PDF producer needs
  a manual check — see manual-checks.md.)

Single-blind venues (SIGSPATIAL): the opposite failure exists — authors MUST
be listed. The linter skips anonymization there (and `check_template.py`
errors on a leftover `anonymous` documentclass option).

## 5. Missing mandatory sections and statements

| Token in profile | Venue example | Rule |
|---|---|---|
| `neurips-checklist` | NeurIPS | Checklist appended after references via `\answerYes/\answerNo/\answerNA`; **missing checklist = desk reject**; excluded from page limit |
| `icml-impact-statement` | ICML | Impact Statement after acknowledgements, before references; excluded from page limit |
| `ai-use-acknowledgement` | ICDE 2026 | Mandatory "AI-Generated Content Acknowledgement" naming the AI system and affected sections; AI cannot be an author |
| `coi-declaration` | ICDE | Missing COI declarations = desk reject — but COI is declared **in CMT**, not the PDF, so the in-paper check is a WARN with a pointer |
| `ccs-concepts` | all ACM | `\begin{CCSXML}` block **and** `\ccsdesc` commands, generated at dl.acm.org/ccs |
| `keywords` | ACM / IEEE / LNCS | `\keywords{...}` (ACM, LNCS) or `\begin{IEEEkeywords}` (IEEE) |
| `acm-reference-format` | all ACM | Auto-generated by acmart; `printacmref=false` is tolerated in review but must be re-enabled for camera-ready |
| `ethics-statement`, `reproducibility-statement` | ICLR | Optional — INFO if absent |
| `llm-usage-disclosure` | ICLR 2026 | Required if LLMs contributed significantly |

Unknown tokens degrade gracefully: the linter emits an INFO telling the user
to verify that requirement by hand against the CFP.

## 6. Abstract and keywords

- LNCS mandates 150–250 words and 3–6 keywords separated by `\and`. ACM and
  IEEE conventionally expect ~150–250 words but most CFPs do not mandate a
  number — the profile stores `abstract_words: null` and the linter reports
  the count against the norm without failing it.
- NeurIPS asks for a one-paragraph abstract; a blank line inside the abstract
  is a WARN at NeurIPS-style venues.
- Citations and URLs in the abstract: abstracts are displayed standalone
  (digital libraries, OpenReview, abstract-registration deadlines), where
  `\cite` renders as broken text; URLs there are also an anonymity smell.

## 7. Triggers outside the linter's reach

Real desk-reject triggers a source linter cannot decide — covered in
[manual-checks.md](manual-checks.md):

- compiled-PDF producer metadata; fonts not embedded
- which page the references actually start on
- anonymization of supplementary ZIPs, figures, and linked repos' commit
  history
- dual/concurrent submission and "thin-slice" overlap policies
- submission-form-only requirements (COI in CMT, OpenReview topic selection,
  abstract registration 2–7 days before the paper deadline)
- file-size caps (NeurIPS: 50MB paper PDF, 100MB supplementary ZIP)
- per-author submission caps and resubmission embargoes (ICDE: max 6 papers,
  1-year embargo after rejection)
- hidden prompt-injection text aimed at LLM reviewers (NeurIPS prohibits it;
  treat any white-text/`\textcolor{white}` trick as a serious finding if you
  spot one while reading the source)
