---
name: prepare-camera-ready
description: >-
  Step-by-step camera-ready preparation for accepted papers. Use when a
  researcher says camera-ready, final version, my paper got accepted, or
  mentions ACM eRights, TAPS, ORCID, IEEE PDF eXpress, eCF, OpenReview final
  upload, de-anonymization, or extra camera-ready pages. Resolves the venue's
  rail from a machine-readable profile and walks it end to end. Generates an
  ordered checklist with deadlines and page rules, and lints the final source
  for leftover anonymization and missing rights blocks. Advisory only; it never
  completes forms or submits anything.
---

# Prepare Camera-Ready

Walk an accepted paper through the camera-ready pipeline — the most
error-prone, least documented stage of publishing. The rules are tribal
knowledge split across two big rails (ACM: eRights → ORCID → rights/DOI
block → TAPS; IEEE: PDF eXpress → file naming → eCF → registration) plus the
OpenReview-direct rail used by ML venues. This skill turns the venue profile
into an ordered checklist, walks each form and upload with the user, and
lints the final source for the mistakes that delay or block publication.

## When to use

- "My paper was accepted at SIGSPATIAL / ICDE / NeurIPS — what now?"
- "Help me with the camera-ready / final version."
- "What is this eRights email / TAPS link / PDF eXpress conference ID / eCF?"
- "Do all my coauthors really need ORCIDs?" / "Where does the DOI block go?"
- "How many pages do I get for the camera-ready?" / "How do I de-anonymize?"
- After `write-rebuttal` succeeds; before `make-slides` / talk prep.

## Inputs

1. The acceptance email (ask the user to paste the camera-ready instructions
   from it — they override everything else).
2. The venue profile: `venues/conferences/<venue>-<year>.yml` (schema in
   `venues/schema.yml`; family files supply rail defaults). If missing,
   create one with `parse-cfp` first.
3. The final `.tex` source (the file with `\documentclass`) once editing
   starts; a compiled `.log`/`.pdf` next to it enables the page-count check.

## Process

1. **Resolve the rail and generate the checklist.** Find the profile, ask
   which track the paper was accepted to (camera-ready deadlines and page
   limits differ per track), then run:

   ```
   python3 scripts/camera_ready_checklist.py venues/conferences/<venue>-<year>.yml --track "<track>"
   ```

   It merges the family profile, resolves the rail (`acm-taps`,
   `ieee-pdfexpress`, `openreview-direct`, or other), and prints the ordered
   steps, the venue-specific requirements, the deadline, and the extra-page
   rule. `--json` for machine-readable output.

2. **Re-verify against live sources — mandatory.** Camera-ready instructions
   are issued per acceptance cycle and venues change rails (FAccT left TAPS).
   Before the user acts on anything: read the acceptance email's
   instructions, fetch the venue's camera-ready page, and re-check the
   profile's `cfp_url`. Confirm at minimum: the camera-ready deadline and
   timezone, the page limit and any +page allowance, the rail, and where
   final files are collected (often NOT the review system — ICDE 2026
   explicitly says "do NOT upload camera-ready to CMT"). Update the profile
   YAML if anything differs, and say so.

3. **Walk the rail step by step.** Work through the checklist with the user,
   using the detailed walkthrough for their rail:

   | Rail | Walkthrough | Key gates |
   |---|---|---|
   | `acm-taps` | [references/acm-taps-rail.md](references/acm-taps-rail.md) | eRights email (corresponding author, check spam), ORCID for ALL authors, rights/DOI block in the preamble, SOURCE zip to TAPS, PDF+HTML proofs — budget weeks |
   | `ieee-pdfexpress` | [references/ieee-pdfexpress-rail.md](references/ieee-pdfexpress-rail.md) | PDF eXpress conference ID, Xplore validation certificate, file naming (e.g. `PID<n>.pdf`), eCF with EXACT title/author match (cannot be redone), registration/no-show |
   | `openreview-direct` | rail steps in the checklist output + the venue profile | current-year `.sty` with `[final]`, +1 page cap, OpenReview camera-ready task |
   | anything else | venue's own instructions | generic checklist printed by the script; verify everything live |

4. **De-anonymize and apply the +page rules** (blind venues). Do this BEFORE
   any rights form — eRights/eCF need the exact final author list and title.
   Work through
   [references/deanonymize-and-extra-pages.md](references/deanonymize-and-extra-pages.md):
   restore authors/affiliations/ORCIDs, acknowledgments and funding, real
   artifact links, PDF metadata; then fit the paper to the camera-ready page
   budget (never assume an allowance — the reference lists the known rules
   per family).

5. **Lint the final source.** After edits, run:

   ```
   python3 scripts/check_camera_ready.py final.tex \
       --venue venues/conferences/<venue>-<year>.yml --track "<track>"
   ```

   It follows `\input`/`\include` and reports `file:line` findings:
   leftover `review`/`anonymous`/`submission` options, "Anonymous Author"
   placeholders, `anonymous.4open.science` links, missing author block,
   line numbers/todos — plus per rail: ACM rights/DOI block presence and
   placeholder DOI/ISBN values, CCS concepts and `\keywords`; IEEE
   page-number suppression and copyright-notice reminder; NeurIPS-style
   current-year `.sty` with `[final]`. Flags: `--json`, `--strict`,
   `--no-inputs`. Exit codes: 0 clean, 1 errors, 2 usage. Fix and re-run
   until PASS.

6. **Close out the manual gates.** The lint cannot see forms or portals.
   Confirm with the user, one by one: rights form completed (by the
   corresponding author, exact title/author match), validation certificate
   received (IEEE), files uploaded to the right collection site under the
   right name, proofs approved (ACM TAPS), author registration done before
   the registration deadline, and a presenting author committed (no-show =
   removal from the proceedings at IEEE and many ACM venues).

## Output

- An ordered, venue-specific camera-ready checklist with deadline, rail,
  extra-page rule, and re-verification warnings (step 1).
- Concrete edits to the final source (rights block, de-anonymization,
  metadata) applied with the user's approval.
- A lint report (PASS / PASS-WITH-WARNINGS / FAIL with `file:line`) plus the
  list of remaining manual gates and their dates.

## Adapt to your discipline

The rails here are ACM/IEEE/ML-conference specific. For other fields, add
your publisher's rail to the venue family files (e.g. Springer LNCS source
upload, Elsevier/Wiley journal production systems) — the checklist script
reads whatever `camera_ready.requirements` the profile provides.

## Guardrails

- **Never complete eRights, eCF, TAPS, PDF eXpress, or any portal on the
  user's behalf, and never upload anything anywhere.** Prepare, explain,
  lint — the user clicks.
- Rights forms are one-shot in practice (eCF cannot be redone; eRights
  metadata overrides the source). Triple-check title and author list/order
  with the user BEFORE they submit a form.
- Never guess deadlines, conference IDs, ISBN/price strings, or DOI values —
  they come from the acceptance email, the live venue page, or the completed
  rights form. Profiles are a starting point, never ground truth (step 2 is
  not optional).
- Page budgets: never assume a camera-ready extra-page allowance that is not
  stated by the venue for this year.
- New or changed citations during camera-ready edits go through
  `verify-citations` before they enter the .bib.
- Quote at most the flagged line of the user's paper in reports; never
  reproduce paper text at length, and never bundle paper content into the
  repo.
