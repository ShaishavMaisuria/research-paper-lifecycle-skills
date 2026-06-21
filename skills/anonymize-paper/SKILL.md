---
name: anonymize-paper
description: Deep anonymization sweep for double-blind paper submissions, plus clean de-anonymization for camera-ready. Use when a researcher says "anonymize my paper", "double-blind check", "blind this submission", "remove author names", "did I leak my identity" — or, after acceptance, "de-anonymize" / "restore authors for camera-ready". Sweeps the whole leak surface, \author/\affiliation/\email/\orcid/\thanks, acknowledgments and grant numbers, hyperref pdfauthor and compiled-PDF metadata, first-person self-citations (rewritten to third person), GitHub/dataset/homepage links vs anonymized mirrors, LaTeX comments, .bib annotations, home-directory paths, and supplementary material (.git dirs, notebooks, LICENSE/AUTHORS files). Bundles a stdlib-only scanner (scan_anonymization.py, check ids shared with preflight-check) and a reversible-edit workflow (toggle + manifest) so every change is cleanly undone at camera-ready. Advisory only; never submits anything.
---

# Anonymize Paper

Make a LaTeX submission genuinely double-blind — then undo it cleanly after
acceptance. Anonymization leaks are documented desk-reject grounds (CHI and
NeurIPS state this explicitly, including leaks in supplementary material and
linked repos), and de-anonymization done by hand routinely leaves placeholder
authors or dead `anonymous.4open.science` links in the published PDF. This
skill runs the deep sweep in both directions and records every change so the
reversal is mechanical, not archaeological.

## When to use

- "Anonymize my paper for NeurIPS / CHI / ICML / KDD ..." / "blind this"
- "Did I leak my identity anywhere?" / "double-blind check" before submission
- "Rewrite my self-citations in third person"
- "My code/data links identify me — what do I do?"
- After acceptance: "de-anonymize", "restore the authors", "prepare the
  camera-ready author block"
- Called from `tailor-to-venue` (anonymization sweep step) or before
  `preflight-check` (final gate).

## Inputs

1. The main `.tex` file (with `\documentclass`); `\input`/`\include` files
   are followed automatically.
2. The venue profile `venues/conferences/<venue>-<year>.yml` (schema in
   `venues/schema.yml`) — supplies the blind level (single/double/triple) and
   the `cfp_url`. No profile? Ask the user for the blind level or create a
   profile with `parse-cfp`.
3. Optional but recommended: the compiled PDF (metadata check), the
   supplementary directory, and the author/institution names to grep for.

## Process — anonymize (submission)

1. **Resolve the blind level, then re-verify it live — mandatory.** Read the
   venue profile; fetch the `cfp_url` and confirm the blind level and the
   venue's anonymization policy wording (what counts as a violation, whether
   acknowledgments must be removed, whether anonymized artifact links are
   allowed). Single-blind venues (e.g. SIGSPATIAL) need *no* anonymization —
   tell the user and stop instead of mangling a fine paper.

2. **Run the deep scan:**

   ```
   python3 scripts/scan_anonymization.py paper.tex \
       --venue venues/conferences/<venue>-<year>.yml \
       --supplementary <supp-dir> --names "Jane Doe,Example University"
   ```

   Flags: `--blind double` (no profile), `--pdf paper.pdf` (explicit PDF),
   `--no-pdf`, `--json`, `--strict` (warnings also fail), `--force` (scan at
   single-blind venues anyway), `--no-inputs`. Exit codes: 0 clean, 1 leaks
   found, 2 bad arguments. The scanner covers: author/affiliation/email/
   ORCID/`\thanks` blocks, acknowledgments, funding/grant ids, identifying
   links, bare emails, first-person self-citations, institutional
   self-references, `pdfauthor`, LaTeX comments, `.bib` files, home-directory
   paths, compiled-PDF metadata bytes, and the supplementary tree.

3. **Fix findings with reversible edits.** Work through ERRORs first, then
   WARNs (each is a judgment call — discuss, don't bulk-delete). For the fix
   recipe per leak class — author block, acknowledgments, self-citations,
   repo/dataset links, metadata, supplementary — follow
   [references/leak-catalog.md](references/leak-catalog.md). Two rules:
   - Prefer the `\ifanon` toggle so the camera-ready flip is one line; fall
     back to a `submission-anon` git branch when source will be uploaded
     (arXiv, supplementary zips) — toggles leak the real names in source.
   - Rewrite self-citations in third person ("Doe et al. [12] showed"), never
     as "Anonymous [12]" — unless the cited work is itself unpublished.

4. **Record the reversal manifest.** For every change write one line into
   `anonymization-manifest.md` (kept OUT of the submission zip): what was
   removed/rewritten, file:line, and the exact original text (grant numbers,
   acknowledgment paragraph, real repo URL). Format in
   [references/camera-ready-reversal.md](references/camera-ready-reversal.md).

5. **Sweep the supplementary material.** Re-run step 2 with `--supplementary`
   after fixes. Ship code as a clean export (no `.git`), clear notebook
   outputs/metadata, remove LICENSE/AUTHORS copyright names, and host
   artifacts on an anonymized mirror (anonymous.4open.science) — never Drive/
   Dropbox/GitHub links that expose the account.

6. **Verify the compiled PDF.** Recompile, re-run the scan so the PDF
   metadata check runs on the fresh PDF, and do the manual pass the scanner
   cannot: figures with lab logos or terminal screenshots showing usernames,
   dataset descriptions that name the institution, watermarks.

7. **Re-run until clean, then gate.** Iterate scan → fix → scan to exit 0.
   Then run the full `preflight-check` (it validates the documentclass
   invocation and the rest of the desk-reject surface).

## Process — de-anonymize (camera-ready)

8. After acceptance, reverse using the manifest plus:

   ```
   python3 scripts/scan_anonymization.py paper.tex --mode camera-ready
   ```

   This flags the leftovers: placeholder/empty author blocks, lingering
   `anonymous.4open.science` links, `[review,anonymous]` class options,
   `neurips_<year>` without `[final]`, `\anontrue` toggles, "omitted for
   review" wording, and missing acknowledgments. Restore the author block so
   it matches the copyright form (ACM eRights / IEEE eCF) EXACTLY — walk
   [references/camera-ready-reversal.md](references/camera-ready-reversal.md)
   — then hand off to `prepare-camera-ready` for the venue rail.

## Output

- A findings report (text or `--json`) with severity, check id, `file:line`.
- The edited `.tex`/supplementary files (with the user's approval, one leak
  class at a time) plus `anonymization-manifest.md` for the reversal.
- At camera-ready: a leftover report and the restored sources.

## Relationship to preflight-check

`preflight-check` runs the same source-level anonymization checks (shared
check ids, `anonymization/*`) as one gate among many; this skill is the deep
variant — comments, `.bib`, PDF bytes, supplementary trees, name grep — plus
the fix workflow and the camera-ready reversal. Quick gate → preflight; full
sweep or de-anonymization → this skill.

## Adapt to your discipline

The leak patterns are field-agnostic; the policies are not. Fork and swap the
venue profiles for your field's journals (many use single-blind — the scan
then auto-skips), and extend `--names` conventions for institutional review
boards or clinical-trial registry ids that identify groups in your field.

## Guardrails

- Never claim the paper "is anonymous" — say "no machine-detectable identity
  leaks remain"; writing style, self-datasets, and niche topics can still
  identify authors, and reviewers actively search.
- Never delete scholarly content to anonymize (e.g. dropping a self-citation
  entirely is misconduct-adjacent); rewrite in third person instead. Citation
  integrity questions route through `verify-citations`.
- Re-verify the blind level and anonymization policy against the live
  `cfp_url` before editing — a wrong blind level mangles a correct paper.
- Never submit to any system on the user's behalf; stop at the report/edits.
- Quote at most the flagged line in reports; never paste large paper
  portions into outputs.
