# Reproducibility standards & badge taxonomy — a map to verify, not memorize

This is a **map of what to check**, assembled to orient the skill. Every fact
here can change per venue, per year. Before stating any of it to the author,
**re-verify it against the venue's current Call for Artifacts / checklist** and
give a clickable source and access date. A stale badge
rule misleads an author the same way a stale page limit does.

## The three independent badge families (ACM Artifact Review & Badging v1.1)

ACM v1.1 is the current taxonomy (v1.0 badges were issued up to 2020-05-14).
Three **independent** families — an artifact can earn any combination:

1. **Artifacts Available** — author-created artifacts placed on a **publicly
   accessible ARCHIVAL repository with a DOI / persistent identifier** (not just
   a personal or GitHub URL). Independent of whether they were evaluated.
2. **Artifacts Evaluated** — two tiers:
   - **Functional** — documented, consistent, complete, exercisable, with
     evidence of verification/validation.
   - **Reusable** (higher; subsumes Functional) — additionally well-structured
     and carefully documented so others can reuse/repurpose beyond the paper.
   - Reviewers may see artifacts privately; public availability is **not**
     required for this family.
3. **Results Validated** — two tiers:
   - **Reproduced** — main results obtained by a **different team USING** the
     author-supplied artifacts (in part).
   - **Replicated** — main results obtained by a different team **WITHOUT** the
     author-supplied artifacts (independent re-implementation).

Source to confirm: `acm.org/publications/policies/artifact-review-and-badging-current`.

### ⚠ The Reproduced/Replicated swap (a live trap)

ACM **swapped** the definitions of *Reproduced* and *Replicated* after
**2020-05-14** (on NISO's advice, aligning to NISO RP-31-2021). **Pre-2020
(v1.0) papers use the INVERSE meanings.** Always check the badge era before
interpreting these words. Sources: `acm.org/publications/badging-terms`;
NISO RP-31-2021.

## Exact match is never required — anywhere

ACM, the SIGMOD ARI, and ETAPS/EAPLS all require only that results agree
**within a tolerance that does not change the paper's main claims** ("similar
behavior"). A skill that demands bit-exact reproduction gives wrong advice.
This is why `compare_metrics.py` is tolerance-aware (`--rel-tol`/`--abs-tol`)
and never tests for equality.

## Archival hosting is specific (don't say "just push to GitHub")

- **USENIX-family** (e.g. USENIX Security) *Artifacts Available* explicitly
  **rejects GitHub/personal sites** for the permanent copy — it must be
  **Zenodo / FigShare / Dryad** with a **version-specific DOI**.
- **Zenodo** gives an *extrinsic* DOI; mind **concept DOI** (always-latest) vs
  **version DOI** (one immutable release). CFAs want a **version DOI for the
  final**; a concept DOI is usually acceptable *during* evaluation.
- **Software Heritage** gives *intrinsic*, content-addressed **SWHIDs**
  (`swh:1:...`), resolvable without a registry; SWHID became **ISO/IEC 18670**
  (2025-04-23). DOIs and SWHIDs are **complementary**, not interchangeable.

## Badge offerings vary per venue per year — examples to re-verify

These are **illustrative snapshots**; confirm the cycle you are targeting.

| Venue (cycle) | What to expect — RE-VERIFY at the live CFA |
|---|---|
| **OSDI '26** | Evaluating **only Artifacts Available** this cycle; Zenodo DOI encouraged. (Shows offerings change year-to-year even within a venue.) |
| **SOSP 2026** | Cooperative, single-blind; pipeline register → submit (GitHub etc.) → kick-the-tires → main eval → final **Zenodo deposit with DOI**. All-badge artifacts eligible for a Distinguished Artifact award. |
| **USENIX Security 2026** | Phase-1 *Artifacts Available* **mandatory**, permanent public hosting (Zenodo/FigShare/Dryad, **not GitHub**) with a version DOI. Phase-2 optional: Functional + Results Reproduced via a ≤3-page artifact-appendix PDF (per-claim reproduction + comparison method). |
| **SIGMOD ARI** | **Optional, POST-acceptance** (separate Call, weeks after camera-ready). Awards Available, Evaluated–Reusable, Results Reproduced. "Reproducible" = recreate result data + graphs with **similar behavior**; exact match not required. |
| **ETAPS / EAPLS** | Same 3-family structure, explicitly "based on the ACM recommendations." Canonical non-ACM-but-aligned example. |

## Mandatory checklists (desk-reject gates) — asymmetric failure mode

- **NeurIPS Paper Checklist** — **mandatory**, 16 sections (Claims; Limitations;
  Theory; Experimental-Result Reproducibility; Open Access to Data & Code;
  Experimental Setting; Statistical Significance; Compute Resources; Code of
  Ethics; Broader Impacts; Safeguards; Licenses; Assets; Crowdsourcing & Human
  Subjects; IRB; LLM-usage). Each Yes/No/NA **with a 1–2 sentence
  justification**. **Missing checklist = desk reject**, but an honest *no/n.a.*
  with justification is **never** grounds for rejection. Push authors to file
  **accurately**, not to game every box to "yes".
- **NeurIPS Code Submission Policy** — code **not mandatory** ("no, proprietary"
  is acceptable; cannot reject solely for missing code *unless code is the
  contribution*, e.g. a benchmark), but a **reasonable reproducibility avenue**
  is required. Review-phase code must be **anonymized** in one ZIP (<100 MB);
  de-anonymize at camera-ready.
- **ML Code Completeness Checklist** (paperswithcode; used by NeurIPS) — the 5
  items `audit_repo.py` checks: (1) dependency spec; (2) training code;
  (3) evaluation code; (4) pretrained models; (5) README with a **results table
  AND the exact command to reproduce each number**.
- **ACL Rolling Review "Responsible NLP"** — **mandatory**, 5 sections (A
  Limitations+Risks [Limitations compulsory]; B Artifacts [license/use/PII];
  C Computational Experiments [#params + total compute/GPU-hours +
  infrastructure; hyperparameter search; error bars vs single run];
  D Annotators; E AI-assistant disclosure). **ARR desk-rejects
  incomplete/misleading filings (since Dec 2024).**
- **CVPR 2026** — code submission strongly encouraged as supplementary
  (reviewers *may* check it); **new: a mandatory Compute Reporting Form (CRF)**.

## Anonymized artifacts for double-blind review

- **Anonymous GitHub** (`anonymous.4open.science`) is the de-facto tool —
  proxies a repo, scrubs owner/name + user-listed identifying terms across
  filenames and contents, refreshes on push, has a CLI to emit a local ZIP.
- Alternative: submit an **anonymized ZIP** via the supplementary system.
- Anonymization must also cover code comments, commit history, config files,
  LICENSE/AUTHORS, and any embedded emails/URLs — not just the README.
  `audit_repo.py --blind double` scans the README; the rest is a manual pass.
