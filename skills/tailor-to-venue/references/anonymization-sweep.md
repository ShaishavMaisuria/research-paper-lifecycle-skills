# Anonymization sweep plan

How to take a draft to the venue's blind level — or back. Pair with
`scripts/anon_sweep.py`, which finds the mechanical leaks; this file is the
fix strategy per category and the judgment calls the script cannot make.

Blind level comes from the venue profile (`review.blind`) — re-verify on the
live CFP. Anonymization violations are a desk-reject trigger at double-blind
venues even when accidental.

## Contents

- [Blind levels](#blind-levels)
- [Leak categories and fixes](#leak-categories-and-fixes)
- [Beyond the PDF](#beyond-the-pdf)
- [Preprint and prior-version policy](#preprint-and-prior-version-policy)
- [De-anonymizing (the reverse sweep)](#de-anonymizing-the-reverse-sweep)

## Blind levels

| Level | Authors see reviewers | Reviewers see authors | Extra rule |
|---|---|---|---|
| single | no | YES — names/affiliations REQUIRED on the submission | omitting authors at a single-blind venue is itself a gap |
| double | no | no | everything in this file applies |
| triple | no | no | identity also hidden from chairs/ACs: scrub submission-system fields, cover letters, and any prior-review responses |

## Leak categories and fixes

Work through anon_sweep.py findings in this order:

1. **Author block / affiliation / email / ORCID.** Prefer the template's
   mechanism over manual blanking: `anonymous` option for acmart (with
   `review`), the NeurIPS-style default (no `final`). For IEEEtran (no such
   option) replace with "Anonymous Author(s)" / "Anonymous Institution".
   Delete `\thanks{}` and `\titlenote{}` contents entirely.
2. **Acknowledgments + funding.** Remove the whole section AND inline funding
   phrases ("supported by NSF grant #...") — grant numbers are publicly
   searchable and identify the lab instantly. Keep the text in a
   `camera-ready-restore.md` file next to the draft.
3. **First-person self-citations.** Rewrite to third person, citing your own
   prior work as if by others: "Our previous work [7] showed" → "Prior work
   by Chetty et al. [7] showed" (CHI's canonical example). Do NOT omit the
   citation — uncited closely-related own work looks like plagiarism to
   reviewers. Exception: if citing it in third person STILL identifies you
   (your system's unique name), cite as "[anonymized for review]" only where
   the CFP sanctions that form.
4. **Repository / dataset / project links.** Replace with an anonymized
   mirror (anonymous.4open.science or the venue's sanctioned mechanism), or
   "link omitted for review". Check the README, LICENSE, commit authors, and
   issue history of the mirror itself — reviewers click.
5. **PDF metadata.** Set empty author metadata via `hyperref`:
   `\hypersetup{pdfauthor={},pdftitle={<title>}}`, recompile, then re-run
   `anon_sweep.py --pdf`. Note the script reads only uncompressed metadata —
   confirm with `pdfinfo`/`exiftool` if available.
6. **Soft signals** (script severity REVIEW): institution-describing phrases
   ("our university's cluster" → "a 64-node cluster"), IRB approval numbers
   (state approval without the number/institution if the CFP allows),
   region-identifying datasets ("our campus dataset" → described neutrally),
   and mentions of concurrent submissions.

## Beyond the PDF

The sweep is not done at the main PDF:

- **Supplementary materials**: code zips (check file headers, notebook
  metadata, paths like `/home/jane/...`), video figures (voices, lab logos),
  data files (creator fields in spreadsheets).
- **Submission-system fields**: title/abstract fields are fine; "previous
  submission history" or cover-letter fields at triple-blind venues are not.
- **LaTeX sources** when the venue collects them: comments (`% TODO Jane`),
  `\iffalse` blocks, and old text inside `comment` environments survive in
  the archive. Strip comments from any uploaded source.
- **File names**: `smith-kdd-resubmission.pdf` leaks in two ways at once.

## Preprint and prior-version policy

Policies differ — read the CFP section on dual submission/preprints, and
record the answer in the plan:

- Many ML venues permit arXiv preprints and merely forbid AUTHORS advertising
  them during review; the paper itself must not link its own preprint.
- Some double-blind venues forbid posting updated preprints during review.
- Workshop versions: when the CFP requires declaring them, do it in the
  submission form, not in the anonymized PDF.

Do not state a venue's preprint policy from memory — quote the live CFP in
the plan, or mark it "unknown — check CFP".

## De-anonymizing (the reverse sweep)

Two situations need the reverse pass:

1. **Retargeting double-blind → single-blind** (e.g. a KDD-style draft going
   to SIGSPATIAL, which requires authors listed): restore names,
   affiliations, emails; restore first-person framing where it reads better;
   keep funding info out until camera-ready unless the CFP wants it at
   submission. `anon_sweep.py --level single` flags leftover placeholders.
2. **Camera-ready after acceptance**: restore the author block exactly as
   registered in the submission system (the camera-ready rails check
   title/author match), restore acknowledgments from
   `camera-ready-restore.md`, drop `anonymous`/`review` class options, and
   re-link the real repository. Hand off to the `prepare-camera-ready` skill.

Keep `camera-ready-restore.md` updated during anonymization — every removal
recorded with its original text and location. Future-you at the camera-ready
deadline will not remember which grant numbers went where.
