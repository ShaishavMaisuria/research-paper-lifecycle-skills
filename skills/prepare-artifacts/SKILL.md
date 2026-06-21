---
name: prepare-artifacts
description: Prepares a reproducibility artifact (code/data) for submission and badging. Use when a researcher says "artifact evaluation", "artifact appendix", "reproducibility", "badge", "Artifacts Available/Evaluated/Functional/Reusable", "Results Reproduced/Replicated", "ACM badging", "USENIX/OSDI/SOSP AE", "SIGMOD ARI", "NeurIPS code/checklist", "ACL repro checklist", "Zenodo DOI", "Software Heritage", "anonymize my code/repo", or "package my code". Builds the artifact README + appendix, the dependency/run instructions, an anonymized repo for double-blind, and archival-DOI (Zenodo version vs concept) / Software Heritage SWHID guidance; resolves the ACM badge taxonomy and the Reproduced/Replicated era swap; and lints the artifact directory against the ML Code Completeness checklist with bundled stdlib-only scripts. Outputs an artifact-readiness checklist + packaging plan. Re-verifies the venue current artifact rules live. Advisory only; never submits.
---

# Prepare Artifacts

Turn a research codebase into a **submittable, badge-ready reproducibility
artifact**. Artifact evaluation is a separate, post-acceptance track at most
systems/PL/ML venues with its own deadline, its own appendix, and badges that
**change per venue per year** — this skill builds the package (README,
appendix, run instructions, anonymized repo, archival deposit guidance),
produces an artifact-readiness checklist and a packaging plan, and lints the
artifact directory for the bars reviewers actually check.

It does not run the author's experiments or claim a result reproduces — it
prepares and checks the package, and tells the author exactly what reviewers
will verify by hand.

## When to use

- "My paper was accepted — how do I do the artifact evaluation / get a badge?"
- "Package / clean up my code for submission." / "anonymize my repo for review."
- "What's an artifact appendix / Artifacts Available / Functional / Reusable?"
- "Do I need a Zenodo DOI? concept vs version?" / "Software Heritage?"
- "Fill out the NeurIPS code/reproducibility or ACL repro checklist."
- "What does Reproduced vs Replicated mean for this badge?"
- Alongside `prepare-camera-ready` (de-anonymization + final deposit overlap).

## Inputs

1. The **artifact directory** — the code/data repo to be packaged (path).
2. The target **venue + track**, and ideally `venues/conferences/<v>-<year>.yml`
   (supplies the review **blind level**; create with `parse-cfp` if missing).
   The venue profile does NOT encode the artifact track's badge offering or its
   separate deadline — those are fetched live (step 1).
3. The paper's **major claims** (for a per-claim reproduction plan) and whether
   the artifact is for **review-phase** (often double-blind) or the **final**
   deposit. These change everything (anonymized ZIP vs version DOI).

## Process

1. **Fetch the venue's CURRENT Call for Artifacts — mandatory, live.** Badge
   offerings vary per venue **per year** (OSDI '26 evaluates ONLY "Artifacts
   Available"; SOSP '26 offers all three). Memory and last year are stale by
   construction; verify live. From the live CFA confirm: which
   badges are offered this cycle, the **separate artifact deadline**, the
   archival-hosting requirement, the appendix template/length, and the blind
   model. Snapshots to start from (re-verify, don't trust):
   [references/venue-artifact-rails.md](references/venue-artifact-rails.md).
   Record the chosen badge target + artifact deadline in
   `.paper-memory/decisions.md`.

2. **Resolve the badge taxonomy and the era trap.** Use
   `python3 scripts/badge_advisor.py --badge <name>` to print the ACM v1.1
   families/tiers and, critically, the **Reproduced/Replicated swap**: ACM
   inverted these terms on 2020-05-14, so a pre-2020 badge means the inverse
   (`--era pre-2020`). Reproduction is **never** bit-exact — it must agree
   within a tolerance that does not change the paper's claims. Background:
   [references/badging-standards.md](references/badging-standards.md).

3. **Lint the artifact directory** against the bars reviewers check:

   ```
   python3 scripts/check_artifact.py <artifact_dir> \
       --venue venues/conferences/<v>-<year>.yml [--blind double]
   ```

   It reports, with file paths: the **ML Code Completeness** 5 items
   (dependency spec, training code, evaluation code, pre-trained models or a
   documented way to get them, a README with a **results table + the exact
   reproduce command**); **archival readiness** (GitHub-only vs a DOI/SWHID);
   **double-blind anonymization** (author names/emails, identifying URLs, a
   `.git` directory, PDF/appendix metadata) — driven by the venue's blind level
   or `--blind`; and **hygiene** (a LICENSE, upload-size cap). Flags: `--json`,
   `--strict`, `--zip-cap-mb N`, `--venues-dir`. Exit codes: 0 clean, 1 errors,
   2 usage. The lint covers FILES only — it cannot prove the build runs, that
   results reproduce, or that a DOI resolves.

4. **Build the package the venue asks for** (with the author, not for them):
   - **README** — overview, exact dependency install, **the precise command to
     reproduce each result**, a results table, hardware/runtime expectations,
     and the license. (ML Code Completeness item 5.)
   - **Artifact appendix** — for USENIX-family Phase 2, a **≤3-page PDF** (their
     LaTeX template): hardware/software/config, the paper's **major claims**,
     and a **per-claim reproduction procedure + result-comparison method**
     ("agrees if within X%"). For SIGMOD ARI, include experiment scripts AND
     **graph-generation scripts** ("similar behavior", not exact numbers).
   - **Checklists** — fill the NeurIPS Paper Checklist / Code policy or the ACL
     "Responsible NLP Research" checklist **accurately**: an honest "no"/"n/a"
     with justification is safe; a missing or **misleading** filing is the
     desk-reject (ARR desk-rejects misleading filings since Dec 2024). Do not
     game boxes to "yes."

5. **Anonymize for double-blind review** (if review-phase). Ship an anonymized
   **ZIP without `.git`**, or proxy through **Anonymous GitHub**
   (anonymous.4open.science), listing every identifying term to scrub. Cover
   PDF/appendix metadata, acknowledgments, funding, and self-citation phrasing —
   same rules as the paper (`anonymize-paper`). Details:
   [references/archival-hosting.md](references/archival-hosting.md).

6. **Plan the archival deposit.** For "Artifacts Available," the permanent copy
   must be on an **archival** host — USENIX-family **rejects GitHub/personal
   sites**. Use a **Zenodo version DOI** for the final (a concept DOI is OK only
   *during* evaluation) and/or a **Software Heritage SWHID** (intrinsic,
   ISO/IEC 18670); they are complementary. Add CITATION.cff/codemeta so the
   archive emits citation metadata. De-anonymize and deposit the FINAL version
   at camera-ready (`prepare-camera-ready`).

7. **Write the artifact-readiness checklist + packaging plan** to
   `paper-workspace/submission/artifact-readiness.md` and append a line to
   `paper-workspace/INDEX.md`. Order by severity; cite each finding's source (the lint, the
   live CFA, the badge taxonomy). Re-run the lint until the file-level bars pass.

## Output

- An **artifact-readiness checklist** (PASS / PASS-WITH-WARNINGS / FAIL with
  file paths) plus a **packaging plan**: target badges (from the live CFA),
  hosting (anonymized review copy + final version DOI/SWHID), the completeness
  gaps to close, the appendix/checklist to fill, and the **separate artifact
  deadline**. Written to `paper-workspace/submission/`.
- Draft README / appendix / checklist content the author edits and owns.

## Adapt to your discipline

The badge taxonomy here is ACM/USENIX/SIGMOD/ETAPS/ML-venue specific. For other
fields, swap in your venue's artifact/data-availability rules (e.g. journal
"data availability statements", FAIR data deposits) — the completeness and
anonymization lints read the directory, not a discipline, so they still apply.

## Guardrails

- **Re-verify the venue's CURRENT artifact rules live (step 1 is not
  optional).** Badge offerings change per venue per year; never assume from
  memory or last year. Overconfidence is highest right after a fetch — re-check
  the primary CFA.
- **Never claim a result reproduces, and never demand bit-exact reproduction.**
  ACM/SIGMOD/ETAPS require agreement within a tolerance that doesn't change the
  paper's claims. This skill prepares and checks the package; it does not run
  the experiments or judge the science.
- **The Reproduced/Replicated terms were swapped in 2020** — check the badge era
  (`badge_advisor.py --era`) before interpreting them.
- **Archival hosting is specific:** a GitHub URL is not "Available" for the
  USENIX family — direct authors to a Zenodo version DOI / SWHID.
- **Anonymization-aware:** for double-blind, scrub `.git`, names, emails, URLs,
  and metadata before any review-phase upload.
- **Accurate checklists, not gamed ones:** honest "no"/"n/a" with justification
  is safe; misleading filings get desk-rejected.
- **Copilot, not pilot:** never deposit, never submit to an artifact-evaluation
  system, never complete a checklist form on the author's behalf. Prepare,
  lint, explain — the author clicks.
- Quote at most the flagged line/path; never bundle the author's artifact into
  this repo.

## Memory

Uses the shared `.paper-memory/` convention (full spec:
[`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `lessons.md` (skip re-flagging fixed items; lead with any
  `recurring` packaging habits, e.g. "you tend to ship a `.git` directory") and
  `decisions.md` (the chosen venue/badge target + artifact deadline).
- **At end:** append the target badge + artifact deadline to `decisions.md`, and
  one dated entry per finding worth remembering to `lessons.md` in the shared
  `- [YYYY-MM-DD] (prepare-artifacts | <scope>) issue -> recommendation` format
  (use `reflect-and-improve`'s `reflect_log.py append`, which dedupes/dates).
- Create `.paper-memory/` on demand and offer to add it to the project
  `.gitignore`. Local-only; never upload it or copy it into this repo.
