# Camera-ready reversal — the manifest format and the de-anonymization walkthrough

The reversal is only mechanical if the anonymization recorded itself. This
file defines the `anonymization-manifest.md` contract written during the
submission sweep, then walks the restore step by step. Camera-ready
instructions churn per venue and per year: re-verify everything below against
the acceptance email and the venue's live camera-ready page before editing.

## Contents

- [The manifest contract](#the-manifest-contract)
- [Manifest format](#manifest-format)
- [Reversal walkthrough](#reversal-walkthrough)
- [Template-family specifics](#template-family-specifics)
- [Final verification](#final-verification)

## The manifest contract

- One entry per change made during anonymization — no exceptions. An edit
  without a manifest entry is an edit someone will have to rediscover by
  diffing months later.
- The manifest stores the **exact original text** (acknowledgment paragraphs,
  grant numbers, real repo URLs, the pdfauthor string), not a paraphrase.
- The manifest **never ships**: keep it out of the submission zip, the
  supplementary upload, and any `submission-anon` branch that leaves the
  machine. Add it to `.gitignore` on that branch if needed.
- With the `\ifanon` toggle strategy the `\else` branch already preserves the
  in-source originals — manifest only what lives *outside* the toggle:
  PDF metadata, replaced URLs, supplementary-file edits, deleted comments.
- With the `submission-anon` branch strategy, `main` preserves the source —
  manifest the same out-of-repo items plus anything edited on `main` itself.

## Manifest format

`anonymization-manifest.md`, one `##` block per change, ids `A1, A2, ...`:

```markdown
# Anonymization manifest — <paper title>, <venue-id>, <date>
<!-- DO NOT include this file in any submission/supplementary upload. -->

Strategy: ifanon-toggle | anon-branch (branch: submission-anon)
Scanner: scan_anonymization.py, run <date>, exit 0

## A1 — anonymization/acknowledgments — paper.tex:212
- action: removed \begin{acks}...\end{acks} block
- restore: re-insert verbatim at end of body, before \bibliography
- original:
  ```
  \begin{acks}
  We thank the GeoFlow team. Supported by NSF grant no. 1234567
  and ERC advanced grant 999999.
  \end{acks}
  ```

## A2 — anonymization/identifying-link — paper.tex:96
- action: replaced URL with https://anonymous.4open.science/r/geoflow-ABCD
- restore: point at the permanent artifact (DOI preferred), not the mirror
- original: https://github.com/janedoe/geoflow

## A3 — anonymization/pdf-metadata — paper.tex:8
- action: set \hypersetup{pdfauthor={}}
- original: pdfauthor={Jane Doe, Wei Chen}
```

Required fields per entry: the `check` id from the scanner, `file:line` at
the time of the edit, `action`, and `original`. Add `restore:` notes whenever
the camera-ready value differs from the original (A2 above is the classic
case — the restore target is the *permanent* link, not necessarily the old
one).

## Reversal walkthrough

Work in this order; each step maps to a `reversal/*` check in
`scan_anonymization.py --mode camera-ready`.

1. **Read the camera-ready instructions first.** Acceptance email + the
   venue profile's `camera_ready:` block + the live `cfp_url`. Note the
   extra-page allowance (`camera_ready.extra_pages`) — it decides whether
   the acknowledgments fit back in — and the deadline.

2. **Flip the strategy switch.** Toggle: set `\anonfalse`, then *delete the
   toggle machinery and dead `\ifanon` branches entirely* before any source
   upload (TAPS and arXiv publish source; a dead branch with placeholder
   authors is confusing at best). Branch: merge `submission-anon` away or
   simply continue from `main`, then re-apply any *content* fixes (typo
   fixes, reviewer-requested changes) that landed on the submission branch.

3. **Restore the author block to match the copyright form EXACTLY**
   (`reversal/missing-author`, `reversal/placeholder-author`). Name order,
   spelling, accents, and affiliations must match what was entered in ACM
   eRights / IEEE eCF / the OpenReview author list — mismatches bounce at
   TAPS validation or produce a wrong DOI page. Restore `\orcid{...}` where
   the rail requires it (ACM does).

4. **Restore acknowledgments and funding** (`reversal/
   acknowledgments-missing`). Paste the manifest originals back (`acks`
   environment for acmart; `\section*{Acknowledgments}` elsewhere), grant
   numbers included — funders require the credit line. Confirm the page
   budget with the extra-page allowance from step 1.

5. **Replace every anonymized link** (`reversal/anon-link`).
   `anonymous.4open.science` mirrors expire — a published PDF pointing at
   one is a dead artifact link forever. Point at the permanent repository,
   ideally an archival DOI (Zenodo/OSF release of the tagged version), and
   only secondarily at a live GitHub URL.

6. **Fix class options and placeholder prose** (`reversal/class-option`,
   `reversal/placeholder-text`). Drop `review`/`anonymous` from acmart;
   add `[final]` to `neurips_<year>`/`iclr<year>_conference`, `[accepted]`
   to `icml<year>` (verify the exact option name for the year). Search the
   prose for "omitted for review"-style sentences and restore the real
   content — dataset names, institution mentions in the ethics statement,
   IRB details.

7. **Restore metadata.** Put `pdfauthor` back if the venue's PDF checker
   expects it (IEEE PDF eXpress tolerates either; ACM TAPS regenerates
   metadata). Recompile.

8. **Re-scan and verify** — see below — then hand off to
   `prepare-camera-ready` for the rail itself (eRights/TAPS or PDF
   eXpress/eCF ordering, file naming, DOI/copyright block).

## Template-family specifics

| Family | Submission state | Camera-ready flip |
|---|---|---|
| acmart (sigconf/manuscript) | `[...,review,anonymous]` | drop both options; eRights email supplies the `\setcopyright`/`\acmDOI` block to paste; TAPS validates authors vs eRights |
| neurips-style (`neurips_<yr>.sty`, icml, iclr) | no `final` option (sty hides authors) | add `[final]` (`[accepted]` for icml); authors must match the OpenReview author list, which locks at the deadline |
| IEEEtran | authors blanked manually (no anonymous option) | restore the author block by hand; PDF eXpress validates the PDF, eCF the copyright |
| LNCS (llncs) | `\author`/`\institute` blanked manually | restore both; Springer wants the source zip — strip toggle machinery |

Verify each row against the current year's instructions; option names have
changed across years.

## Final verification

```
python3 scripts/scan_anonymization.py paper.tex --mode camera-ready
```

Target: exit 0 — no placeholder authors, no anonymous mirrors, no
submission class options, no anonymization toggles or "omitted for review"
wording. INFO findings (`reversal/manual`, toggle-off machinery) are
judgment calls; resolve them before uploading source anywhere. Then diff
the camera-ready PDF's first page against the copyright form one last time,
and continue with `prepare-camera-ready`.
