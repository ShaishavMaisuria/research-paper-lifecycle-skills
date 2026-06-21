# Venue artifact rails (snapshots — re-verify the live Call for Artifacts)

Artifact rules and **which badges are offered change per venue per year**. The
notes below are a planning starting point captured from each venue's pages;
they are **not ground truth**. Always fetch the current Call for Artifacts
(CFA) before the author acts, and prefer the acceptance email's instructions
over anything here. The artifact track is almost always a **separate,
post-acceptance** process with its **own deadline** weeks after notification —
a plan that only tracks the paper deadline will miss the artifact window.

## USENIX Security 2026

- Source: https://secartifacts.github.io/usenixsec2026/instructions
- Same 3 badges as ACM.
- **Phase 1 — Artifacts Available is MANDATORY**: permanent public hosting on
  **Zenodo / FigShare / Dryad** (explicitly **NOT** GitHub or personal sites)
  with a **version-specific DOI**.
- **Phase 2 (optional)** — Artifacts Functional + Results Reproduced, requested
  via a **≤3-page artifact appendix PDF** (LaTeX template provided) describing
  hardware/software/config, the paper's **major claims**, and a **per-claim
  reproduction procedure + result-comparison method**.
- Concept DOI allowed during evaluation; version DOI for the final.

## OSDI '26

- Source: https://www.usenix.org/conference/osdi26/call-for-artifacts
- This cycle evaluates **only the "Artifacts Available" badge** — earned when
  the AEC judges artifacts are permanently and publicly available; Zenodo (DOI)
  encouraged.
- Artifact submission ~May 8 2026, decisions ~June 1 2026.
- Lesson: badge offerings vary year-to-year **even within a venue** (OSDI '25
  offered all three). Never assume from a prior year — fetch the current CFA.

## SOSP 2026

- Source: https://sysartifacts.github.io/sosp2026
- Cooperative, **single-blind** (evaluators see authors; authors don't see
  evaluators).
- Pipeline: register → submit (GitHub etc.) → "kick the tires" → main
  evaluation → **final deposit to Zenodo with a DOI** → badges added to the
  camera-ready.
- Artifacts earning **all available badges** are eligible for a Distinguished
  Artifact award.

## SIGMOD Availability & Reproducibility Initiative (ARI)

- Source: https://reproducibility.sigmod.org/
- **Optional, POST-acceptance** (submit shortly after camera-ready via a
  separate Call for Artifacts).
- Awards Artifacts Available, Artifacts Evaluated–Reusable, and Results
  Reproduced, plus up to 3 Best Artifact Awards/year.
- Authors submit: prototype/source + build env, input data (or a generator),
  experiment scripts/workloads, and **graph-generation scripts**.
- **"Reproducible" = recreate the result data and graphs showing SIMILAR
  behavior** to the paper; exact numerical match is NOT required.
- SIGMOD 2026 expects all papers to make code/data/scripts available (helps
  reviewers) but it is not mandatory for acceptance.

## NeurIPS 2026

- Code is **not mandatory** (unless code *is* the contribution), but the
  mandatory **Paper Checklist** and a reasonable reproducibility avenue are.
- Review-phase code is an **anonymized ZIP (<100 MB)**; de-anonymize at
  camera-ready. See `references/badging-standards.md` for the checklists and
  `references/archival-hosting.md` for anonymization.

## ETAPS (PL / verification family)

- ACM-aligned 3-family badges. Functional/Reusable; Available;
  Reproduced/Replicated. Reproduction within tolerance, not exact.
  https://etaps.org/about/artifact-badges

## What the venue profile can and cannot tell you

Local `venues/conferences/<v>.yml` profiles carry the **review blind
level** (used by `check_artifact.py --venue` to drive the anonymization scan)
and the paper-cycle deadlines. They do **not** currently encode the artifact
track's badge offering or its separate deadline — those you fetch live from the
CFA each cycle and, if useful, record in `.paper-memory/decisions.md` so the
next session knows the chosen badge target and the artifact deadline.

## Packaging plan template (what to hand the author)

1. **Target badges** — which the venue offers THIS year (from the live CFA) and
   which the author will go for. Most artifacts should target at least
   Artifacts Available; Functional/Reusable if the track evaluates them.
2. **Hosting** — archival deposit (Zenodo version DOI and/or SWHID); for
   double-blind review-phase, an anonymized ZIP or Anonymous GitHub mirror.
3. **Completeness** — the 5 ML Code Completeness items, or the venue's own
   appendix template (USENIX ≤3-page appendix: hardware/software/config, major
   claims, per-claim reproduction + comparison method).
4. **Anonymization** — for double-blind: scrub names/emails/URLs/`.git`/PDF
   metadata.
5. **License** — a clear license so reviewers may legally run and reuse it.
6. **Deadlines** — the SEPARATE artifact deadline(s); add them to the timeline
   (`plan-submission`).
