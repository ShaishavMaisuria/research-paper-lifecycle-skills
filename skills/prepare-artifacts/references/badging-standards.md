# Artifact badging standards (re-verify each against its live page)

The badge taxonomies below are stable enough to plan against, but **what a
given venue offers changes per year** — always fetch the current Call for
Artifacts. The `scripts/badge_advisor.py` helper prints this taxonomy and
keeps the Reproduced/Replicated terms straight for a given era.

## ACM Artifact Review and Badging v1.1 (the canonical taxonomy)

Policy: https://www.acm.org/publications/policies/artifact-review-and-badging-current
Terms history: https://www.acm.org/publications/badging-terms

Three **independent** badge families — a paper can earn any subset:

1. **Artifacts Available** — author-created artifacts on a publicly accessible
   **archival** repository with a DOI / persistent identifier (NOT a personal
   or GitHub URL). Independent of whether they were evaluated.
2. **Artifacts Evaluated**, two tiers:
   - **Functional** — documented, consistent, complete, exercisable, with
     evidence of verification/validation. May be reviewed privately; public
     availability is **not** required for this badge.
   - **Reusable** (the **higher** tier; subsumes Functional) — additionally
     carefully documented and well-structured so others can **reuse / repurpose**
     it beyond the paper.
3. **Results Validated**, two tiers:
   - **Reproduced** — main results obtained by a **different team USING**, in
     part, the author-supplied artifacts.
   - **Replicated** — main results obtained by a different team **WITHOUT** the
     author artifacts (independent re-implementation).
   - **Exact match is never required** — results must agree within a tolerance
     that does not change the paper's main claims.

### The Reproduced/Replicated era swap (read this twice)

ACM **swapped** the definitions of "Reproduced" and "Replicated" on
**2020-05-14** (v1.0 → v1.1), on NISO's advice, to align with
**NISO RP-31-2021** and other research fields.

- **Current (after 2020-05-14):** Reproduced = different team **with** your
  artifacts; Replicated = different team **without** them.
- **Pre-2020 (v1.0, up to 2020-05-14):** the **inverse** — a pre-2020 paper's
  "Replicated" badge means what "Reproduced" means today.

A skill that hard-codes one definition will mislabel pre- vs post-2020 papers.
Always check the badge era before interpreting these two words.
NISO RP-31-2021: https://www.niso.org/press-releases/2021/01/nisos-recommended-practice-reproducibility-badging-and-definitions-now

## Aligned non-ACM taxonomies

- **ETAPS / EAPLS** (PL & verification): identical 3-family structure
  (Functional/Reusable; Available; Reproduced/Replicated), explicitly "based on
  the ACM recommendations." https://etaps.org/about/artifact-badges
- **SIGMOD Availability & Reproducibility Initiative (ARI)** awards Artifacts
  Available, Artifacts Evaluated–Reusable, and Results Reproduced.

## NeurIPS / ML reproducibility (a different shape — checklists, not badges)

- **NeurIPS Paper Checklist** (https://neurips.cc/public/guides/PaperChecklist):
  **mandatory**, 16 sections, each answered Yes/No/NA with a 1–2 sentence
  justification (required even for NA). A **missing** checklist = desk reject;
  an honest "no"/"n/a" **with justification is never** grounds for rejection.
  Excluded from the page limit.
- **NeurIPS Code Submission Policy**
  (https://neurips.cc/public/guides/CodeSubmissionPolicy): code is **not
  mandatory** ("no, proprietary" is acceptable) UNLESS the code *is* the
  contribution (e.g. a benchmark) — but a reasonable reproducibility avenue is
  required. Review-phase code must be **anonymized** in a single ZIP (<100 MB;
  anonymous URLs for big data); de-anonymize at camera-ready.
- **ML Code Completeness Checklist** (paperswithcode; what `check_artifact.py`
  lints) — exactly 5 items:
  1. dependency specification (requirements.txt / environment.yml / setup.py),
  2. training code, 3. evaluation code, 4. pre-trained models (or a documented
  way to obtain them), 5. a README with a **table of results** AND the **exact
  command** to reproduce each.
  https://github.com/paperswithcode/releasing-research-code

## ACL / NLP

- **ACL Rolling Review "Responsible NLP Research" checklist**: **mandatory**,
  5 sections (A Limitations+Risks — a Limitations section is compulsory;
  B Scientific Artifacts — license, intended use, PII/offensive check, dataset
  stats & splits; C Computational Experiments — #params, total compute/GPU-hours,
  infrastructure, hyperparameter search, error bars; D Human Annotators;
  E AI Assistants). Since **Dec 2024** ARR **desk-rejects** incorrect /
  incomplete / misleading filings.
  https://aclrollingreview.org/responsibleNLPresearch

## CVPR

- CVPR 2026: code submission strongly encouraged as supplementary (reviewers
  **may** check it, not required). **New for 2026:** a mandatory **Compute
  Reporting Form (CRF)**. https://cvpr.thecvf.com/Conferences/2026

## The asymmetric failure mode of checklists

Push authors toward an **accurate** filing, not toward gaming every box to
"yes." NeurIPS desk-rejects a *missing* checklist but never an honest "no"/"n/a"
with justification; ARR desk-rejects *misleading* filings. Honest is safe;
inflated is dangerous.
