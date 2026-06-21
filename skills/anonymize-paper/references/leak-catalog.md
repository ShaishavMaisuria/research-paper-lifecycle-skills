# Identity-leak catalog — what leaks, who desk-rejects, how to fix it reversibly

Fix recipes for every leak class `scan_anonymization.py` reports. Severity
reflects documented venue policy (CHI and NeurIPS both treat anonymization
violations — including in supplementary material and linked repos — as
desk-reject grounds). Policies churn yearly: re-verify the venue's wording
against the live `cfp_url` before applying any of this.

## Contents

- [Blind levels: what each requires](#blind-levels)
- [1. Author block, affiliation, email, ORCID](#1-author-block)
- [2. \thanks, acknowledgments, funding](#2-acknowledgments-and-funding)
- [3. First-person self-citations](#3-self-citations)
- [4. Repository, dataset, and homepage links](#4-links)
- [5. PDF and source metadata](#5-metadata)
- [6. LaTeX comments and .bib files](#6-comments-and-bib)
- [7. Supplementary material](#7-supplementary)
- [8. What the scanner cannot see (manual pass)](#8-manual-pass)
- [Reversible-edit patterns](#reversible-edit-patterns)

## Blind levels

| Level | Meaning | Examples (verify each cycle) |
|---|---|---|
| single | Reviewers see authors; authors don't see reviewers. **Do not anonymize** — names are expected on the submission. | SIGSPATIAL, TKDE, most journals |
| double | Neither side sees the other. Full sweep required. | NeurIPS, ICML, ICLR, CHI, KDD, SIGMOD, CVPR, TODS |
| triple | Double + PC chairs also blinded; usually stricter on supplementary. | ICDM |

The profile field is `review.blind`; `scan_anonymization.py` reads it from
`--venue` (conference value, family fallback) and skips single-blind venues
unless `--force`.

## 1. Author block

Checks: `anonymization/author-block`, `/affiliation`, `/email`, `/orcid`.

- **acmart/LNCS/IEEEtran style venues**: replace content with placeholders —
  `\author{Anonymous Author(s)}`, `\affiliation{\institution{Anonymous
  Institution}}`, `\email{anonymous@example.com}`. With acmart, the
  `anonymous` documentclass option suppresses rendering, but scrub the source
  anyway: submission systems and supplementary zips ship source.
- **NeurIPS-style venues**: the `.sty` hides authors at submission (that is
  why the scanner downgrades the author block to WARN there), but keep the
  source clean if it will be uploaded anywhere.
- **ORCID ids are unique identifiers** — remove `\orcid{...}` entirely at
  submission; restore for camera-ready (ACM requires ORCID at eRights time).

## 2. Acknowledgments and funding

Checks: `anonymization/acknowledgments`, `/thanks`, `/funding`.

- Double-blind venues expect acknowledgments **removed**, not anonymized
  (NeurIPS states no acknowledgments at submission). Cut the whole
  `\begin{acks}`/`\section*{Acknowledgments}` block; save the original text
  verbatim in the manifest — you will want it back at camera-ready, where
  ACM's `acks` environment and grant numbers belong.
- `\thanks{...}` typically carries funding + affiliation: remove or empty it.
- Grant numbers (NSF/ERC/DFG... + digits) are lookup-able to a lab. Remove
  the sentence, manifest the original.
- Institutional self-references ("our university", "our lab") — rewrite
  neutrally: "the authors' institution", "a large public university".

## 3. Self-citations

Check: `anonymization/self-citation`.

Rewrite first person → third person; **never delete the citation** and never
cite yourself as "Anonymous" when the work is published (that itself signals
self-citation and weakens the related-work section).

| Before | After |
|---|---|
| "In our previous work [12] we showed..." | "Doe et al. [12] showed..." |
| "We extend our earlier system [3]." | "This work extends the system of Doe et al. [3]." |
| "...building on our dataset [7]" | "...building on the dataset of [7]" |

- CHI's policy wording is the canonical example: cite your own prior work in
  third person, e.g. "As described by Chetty et al. [10]".
- Exception — the cited work is itself unpublished/under review: cite as
  anonymous supplementary material ("Anonymous [n]", attach if allowed).
- Keep the `.bib` entry intact (real author names in references are expected;
  that is what third-person citation means).
- Sanity check after rewriting: the prose must not still imply ownership
  ("...dataset of [7], which we collected" — still a leak).

## 4. Links

Checks: `anonymization/identifying-link`, `/arxiv-link`, `/link-review`,
`/link-ok`, `/home-path`, `/name-match`.

- GitHub/GitLab/HuggingFace/Drive/Dropbox/Zenodo/OSF links expose the account
  or record owner → replace with an anonymized mirror:
  **anonymous.4open.science** (Anonymous GitHub) is the standard; double-check
  the mirror itself does not render the README's author section.
- Check the venue policy first: some venues (NeurIPS) prefer anonymized code
  via OpenReview supplementary upload rather than external links.
- Own arXiv preprint: do **not** link it; cite it in third person like any
  other reference. (Having a preprint up is usually allowed — linking it from
  the submission is the violation. Verify the venue's preprint policy.)
- Personal homepages (`/~user`, `people.`, `homes.`) — remove.
- Home-directory paths (`/Users/<name>/...` in `\includegraphics`,
  listings, or scripts) leak the username — make paths relative.
- Manifest every replaced URL: camera-ready must point at the real,
  permanent repository (anonymous mirrors expire).

## 5. Metadata

Checks: `anonymization/pdf-metadata`, `/pdf-author`, `/pdf-compressed`.

- In source: `\hypersetup{pdfauthor={...}}` → set empty `pdfauthor={}` for
  submission (manifest the original).
- Compiled PDF: the scanner greps the PDF bytes for `/Author` and XMP
  `dc:creator`; metadata can hide in compressed object streams, so confirm
  with `pdfinfo` / `exiftool` or the viewer's properties dialog when the
  scanner reports `pdf-compressed`.
- pdflatex also embeds creator strings via figures: PDFs exported from
  PowerPoint/Illustrator can carry the author's name in *their* metadata —
  re-export or strip if the venue is strict.

## 6. Comments and .bib

Checks: `anonymization/comment-leak`, `/bib-leak`.

- LaTeX comments are invisible in the PDF but travel with the source —
  uploaded to arXiv (which publishes source), ACM TAPS, or in supplementary
  zips. Delete author headers, emails, TODO lines with repo URLs, and
  copyright lines from comments.
- `.bib` files: scrub `note`/annotation fields that mark self-citations
  ("our paper", "(ours)") and stray contact emails. Entry author fields stay.

## 7. Supplementary

Checks: `anonymization/supplementary-git`, `/supplementary-leak`,
`/supplementary-notebook`.

- **`.git` directories are the classic leak** — `config` and the commit log
  carry name + email. Ship `git archive` output or a clean copy, never a
  clone.
- Jupyter notebooks: metadata + output cells carry usernames and absolute
  paths — clear all outputs and metadata before zipping.
- LICENSE/COPYING/AUTHORS/NOTICE files name the copyright holder — remove or
  genericize for submission, restore at camera-ready.
- Code headers ("# Author: ..."), READMEs with badges pointing at the real
  repo, config files with workstation paths — the scanner flags these
  per-line; fix and re-run with `--supplementary`.
- Videos/screenshots in supplementary: check window titles, menu bars, and
  watermarks frame by frame (manual).

## 8. Manual pass

The scanner is source/byte-level only. Always check by hand:

- Figures: lab logos, institution color schemes, terminal screenshots with
  `user@host` prompts, map screenshots centered on the lab's city.
- Dataset descriptions: "collected from 40 students at <institution>" or an
  IRB protocol number identifies the institution — genericize, keep the IRB
  fact ("approved by the authors' institutional review board").
- Acknowledged datasets/systems only your group has access to.
- The PDF's embedded fonts and figure metadata (see §5).
- Writing tics you cannot fix: accept that anonymity is best-effort; never
  promise more.

## Reversible-edit patterns

Two strategies — pick by whether SOURCE leaves your machine at submission:

1. **`\ifanon` toggle** (PDF-only submission, e.g. most OpenReview venues):

   ```latex
   \newif\ifanon \anontrue   % camera-ready: \anonfalse
   \ifanon
     \author{Anonymous Author(s)}
   \else
     \author{Jane Doe}\affiliation{...}\email{jane@...}
     % acknowledgments, grant numbers, real links live here too
   \fi
   ```

   One-line reversal; the manifest is the `\else` branch itself. **Do not use
   this when source is uploaded** (arXiv, TAPS submission-time source,
   supplementary zips containing the .tex) — the real names ride along.

2. **`submission-anon` git branch** (source leaves the machine): branch,
   apply destructive edits there, keep `main` intact. The reversal is a
   merge; the manifest records anything edited outside the repo (PDF
   metadata, external artifacts).

Either way, maintain `anonymization-manifest.md` (format in
[camera-ready-reversal.md](camera-ready-reversal.md)) — it is the contract
that makes de-anonymization mechanical.
