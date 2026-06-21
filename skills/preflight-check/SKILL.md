---
name: preflight-check
description: >-
  Deterministic desk-reject preflight linter for LaTeX paper submissions. Use
  it when a researcher asks whether a paper is ready to submit, or mentions
  preflight, desk reject, submission check, page limit, anonymization,
  double-blind, missing checklist, or format/template compliance. Lints the
  source against a machine-readable venue profile: documentclass and style
  options, margin/template tampering, anonymization leaks, required sections,
  abstract length, keywords format, and page-limit risk. Runs bundled
  stdlib-only Python scripts; advisory only, never submits anything.
---

# Preflight Check

Run a deterministic desk-reject lint over a LaTeX submission before the
authors hit "submit". Venues explicitly desk-reject — without review — for
page-limit violations, template tampering, anonymization leaks, and missing
mandatory sections. Every one of those is machine-checkable from the source.
This skill catches them while there is still time to fix them.

## When to use

- "Is my paper ready to submit to NeurIPS / SIGSPATIAL / CHI / ...?"
- "Check my paper for desk-reject risks" / "run a preflight"
- "Did I anonymize this properly?" / "double-blind check"
- "Am I over the page limit?" / "is my template compliant?"
- Right after `tailor-to-venue`, and always before any actual submission.

## Inputs

1. The main `.tex` file of the submission (the one with `\documentclass`).
   `\input`/`\include` files are followed automatically.
2. A venue profile: `venues/conferences/<venue>-<year>.yml` (schema in
   `venues/schema.yml`). If the venue has no profile yet, create one first
   with `parse-cfp` (or copy the nearest family file and fill it in).
3. Optional but strongly recommended: a compiled `.log` or `.pdf` next to the
   `.tex` (same basename) so the page-count risk check can run.

## Process

1. **Resolve the venue profile.** Find the matching file under
   `venues/conferences/`. Confirm the year matches the target deadline cycle.
   Ask the user which track they are submitting to — page limits differ per
   track (e.g. SIGSPATIAL Research = 10 pages excl. references, Demo = 4
   incl.). Sanity-check the merged profile with:
   `python3 scripts/venue_profile.py venues/conferences/<venue>.yml --track <name>`

2. **Re-verify critical facts against the live CFP — mandatory.** Profiles
   are a starting point, never ground truth; a stale page limit causes the
   exact desk reject this skill exists to prevent. Fetch the profile's
   `cfp_url` and confirm: page limit + what it excludes, blind level,
   template invocation, required sections, and the deadline. If anything
   differs, update the profile YAML first and say so in the report.

3. **Run the full preflight:**

   ```
   python3 scripts/run_preflight.py paper.tex \
       --venue venues/conferences/<venue>-<year>.yml --track "<track>"
   ```

   Or run checkers individually when the user asks about one dimension:

   | Script | Checks | Run |
   |---|---|---|
   | `scripts/check_template.py` | documentclass + options vs profile, year-versioned .sty (NeurIPS/ICML/ICLR), geometry/savetrees/fullpage, `\setlength` on layout dims, `\linespread`<1, negative `\vspace` patterns, column count, page-limit risk from `.log`/`.pdf` | `python3 scripts/check_template.py paper.tex --venue <yml> --track <t>` |
   | `scripts/check_anonymization.py` | `\author`/`\affiliation`/`\email`/`\orcid`/`\thanks` content, acknowledgments sections, funding/grant lines, identifying links (GitHub, personal pages) vs anonymized mirrors, first-person self-citations, hyperref `pdfauthor` | `python3 scripts/check_anonymization.py paper.tex --venue <yml>` |
   | `scripts/check_sections.py` | every `format.required_sections` token: NeurIPS checklist, ICML impact statement, AI-use acknowledgement (ICDE), COI declaration, CCS concepts + `\keywords`, plus title/abstract/bibliography presence | `python3 scripts/check_sections.py paper.tex --venue <yml>` |
   | `scripts/check_abstract.py` | abstract word count vs venue bounds (or the 150–250 norm), single-paragraph rule, citations/URLs in abstract, keywords format (ACM/IEEE Index Terms/LNCS 3–6) | `python3 scripts/check_abstract.py paper.tex --venue <yml>` |

   Useful flags on every script: `--json` (machine-readable), `--strict`
   (warnings also fail), `--track <substring>`, `--venues-dir <dir>` (when the
   profile lives outside this repo), `--no-inputs`. Anonymization adds
   `--force` to scan even at single-blind venues.

4. **Interpret severities for the user.**
   - `ERROR` — documented desk-reject grounds at this venue. Must fix.
   - `WARN` — judgment call (e.g. one negative `\vspace` is normal; eight is
     space compression). Walk through each with the user.
   - `INFO` — confirmations and pointers to manual checks. Do not pad the
     report with these; summarize.
   Exit codes: 0 = no errors, 1 = errors found (or warnings with `--strict`),
   2 = bad arguments/missing files.

5. **Do the manual checks the linter cannot do.** Source-level linting
   cannot see compiled-PDF metadata, where the references actually start,
   supplementary files, or submission-form fields (COI declarations at ICDE
   live in CMT, not the PDF). Work through
   [references/manual-checks.md](references/manual-checks.md) with the user.

6. **Fix and re-run until clean.** Quote each finding's `file:line`, propose
   the minimal edit, apply it if asked, and re-run the affected checker.
   For the reasoning behind each check (which venue desk-rejects for what,
   with sources), see
   [references/desk-reject-triggers.md](references/desk-reject-triggers.md).

## Output

A findings report (text or `--json`) per checker or combined via
`run_preflight.py`: severity, check id, `file:line`, message, summary counts,
and a PASS / PASS-WITH-WARNINGS / FAIL verdict. Present it to the user as a
fix-list ordered by severity, then offer to apply fixes one at a time.

## Adapt to your discipline

Profiles target CS venues (ACM/IEEE/ML/LNCS). For other fields, fork and add
venue YAMLs with your journals' rules — the checkers only read the profile,
so new disciplines need data, not code.

## Guardrails

- A clean preflight is necessary, not sufficient — never tell the user the
  paper "will not be desk-rejected"; say "no machine-checkable desk-reject
  triggers found".
- Always re-verify page limits/deadlines/policies against the live `cfp_url`
  before the user relies on them (step 2 is not optional).
- Never submit to any system on the user's behalf; stop at the report.
- Never paste large portions of the user's paper into the report — quote at
  most the flagged line.
- Citation problems are out of scope here: route them through
  `verify-citations`.
