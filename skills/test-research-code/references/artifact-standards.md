# Artifact-evaluation standards (badges, archival, anonymization)

Reference for `test-research-code`. **Re-verify every venue-specific fact against
the live Call for Artifacts before relying on it** — badge offerings change per
venue *per year*, and a model's memory of them is stale by construction
Always re-check live venue guidance before treating these notes as current. The
durable facts below are the *shape* of the landscape, not a substitute for the
current CFA.

## The three independent badge families (ACM v1.1, current)

ACM **Artifact Review and Badging v1.1** is the canonical scheme; most CS venues
(USENIX, SIGMOD ARI, ETAPS/EAPLS) align to it. The three families are
**independent** — a paper can earn any subset.

1. **Artifacts Available** — author artifacts are placed on a **publicly
   accessible, archival** repository with a **DOI / persistent identifier**.
   - About *availability only*; independent of whether anyone evaluated them.
   - A bare GitHub or personal URL is **not** archival. USENIX-family explicitly
     **requires Zenodo / FigShare / Dryad** (or similar) with a DOI and
     **rejects** GitHub/personal sites for the permanent copy.

2. **Artifacts Evaluated** — reviewers exercised the artifact. Two tiers:
   - **Functional** — documented, consistent, complete, **exercisable**, with
     evidence of verification/validation.
   - **Reusable** — the **higher** tier; subsumes Functional and is additionally
     carefully documented and well-structured so others can **reuse/repurpose**
     it beyond the paper.
   - Reviewers may see artifacts **privately**; public availability is *not*
     required for this family.

3. **Results Validated** — a different team obtained the paper's main results.
   Two tiers, and **this is the terminology trap** (see below):
   - **Reproduced** — main results obtained by a **different team USING, in
     part, the author-supplied artifacts**.
   - **Replicated** — main results obtained by a different team **WITHOUT** the
     author artifacts (independent re-implementation).

### The Reproduced / Replicated swap (a live trap)

ACM **swapped** the definitions of *Reproduced* and *Replicated* after
**2020-05-14** (v1.0 → v1.1), on NISO's advice, to match **NISO RP-31-2021**.
So a **pre-2020 (v1.0)** paper uses the **inverse** meanings of the two words.

- **Check the badge era before interpreting either word.** Badges issued up to
  2020-05-14 are v1.0 (old/inverse); after that, v1.1 (current, above).
- Sources: acm.org/publications/policies/artifact-review-and-badging-current,
  acm.org/publications/badging-terms, NISO RP-31-2021.

### "Reproduce" never means bit-exact

ACM, SIGMOD ARI, and ETAPS all require only agreement **within a tolerance that
does not change the paper's main claims** ("similar behavior"). A skill that
demands bit-identical numbers gives wrong advice. State expected runtime and the
tolerance, not an exact-match promise.

## Venue snapshots (verify the current CFA — these drift year to year)

- **USENIX Security 2026** — same 3 badges. **Phase 1 Artifacts Available is
  mandatory**, requires permanent public hosting (Zenodo/FigShare/Dryad) with a
  **version-specific DOI**. Phase 2 (optional): Functional + Results Reproduced,
  requested via a ≤3-page **artifact appendix PDF** (LaTeX template) giving
  hardware/software/config, the paper's major claims, and a **per-claim
  reproduction procedure + result-comparison method**. Concept DOI OK during
  evaluation; version DOI for final.
- **OSDI '26** — evaluating **only Artifacts Available** this cycle. Zenodo DOI
  encouraged. (Proof that offerings vary per year even within a venue.)
- **SOSP '26** — cooperative, single-blind (evaluators see authors). Pipeline:
  register → submit (GitHub etc.) → "kick the tires" → main evaluation → final
  **deposit to Zenodo with DOI** → badges on camera-ready. All-badges artifacts
  are eligible for a Distinguished Artifact award.
- **SIGMOD ARI** — **optional, post-acceptance** (separate Call for Artifacts
  shortly after camera-ready). Awards Available, Evaluated–Reusable, Results
  Reproduced, + Best Artifact Awards. "Reproducible" = recreate result data and
  graphs showing **similar behavior**; exact numbers not required. Authors submit
  source + build env, input data (or a generator), experiment scripts, and
  graph-generation scripts.
- **ETAPS / EAPLS** (PL & verification) — identical 3-family structure,
  explicitly "based on the ACM recommendations." The canonical non-ACM-aligned
  example.
- **NeurIPS 2026** — code is **not** mandatory (a "no, proprietary" answer is
  acceptable; cannot reject solely for missing code *unless the code is the
  contribution*), but a **reasonable reproducibility avenue is required**. The
  mandatory **Paper Checklist** (16 sections) and the **ML Code Completeness
  Checklist** (5 items) are the operative artifacts — see
  [`repro-essentials.md`](repro-essentials.md). Review-phase code must be
  **anonymized** in a single ZIP (<100MB; anonymous URLs for big data);
  de-anonymize at camera-ready.
- **CVPR 2026** — code submission *encouraged* as supplementary (reviewers may
  check it; not required). New: a mandatory **Compute Reporting Form**.
- **ACL Rolling Review** — Responsible-NLP checklist **section C** governs
  computational experiments (#params, total compute/GPU-hours, infrastructure,
  hyperparameter search, error bars). Mandatory; ARR desk-rejects
  incomplete/misleading filings since Dec 2024.

## Archival hosting: DOIs vs SWHIDs (complementary, not interchangeable)

- **Zenodo** gives an **extrinsic DOI**. Key distinction:
  - **Concept DOI** = always-latest (resolves to the newest version).
  - **Version DOI** = one immutable release.
  - Artifact committees want a **version DOI** for the final, so reviewers
    evaluate *exactly what is published*. A concept DOI is OK *during*
    evaluation only. Pointing reviewers at a concept DOI for the final can break
    the "evaluate exactly this" guarantee.
- **Software Heritage** gives **intrinsic, content-addressed SWHIDs**
  (`swh:1:...`) computed by cryptographic hash — resolvable without a registry,
  can pin a file/dir/revision. **SWHID became ISO/IEC 18670 on 2025-04-23**;
  integrated with Zenodo/HAL; can emit BibTeX.
- Use **both** where you can: a Zenodo version DOI for citation + a SWHID for
  intrinsic, registry-independent pinning.

## Anonymization for double-blind

If the artifact is reviewed blind, it must not leak author identity.

- **Anonymous GitHub** (anonymous.4open.science) is the de-facto tool: proxies a
  repo, scrubs owner/org/name + user-listed identifying terms across filenames
  and contents, auto-refreshes on push, and can emit a local anonymized ZIP.
- **Alternative**: submit an anonymized ZIP via the conference supplementary
  system.
- Anonymization must also cover **commit history, notebook metadata, embedded
  paths/usernames, acknowledgments, and self-citation phrasing** — not just the
  README. Hand the actual scrub to `anonymize-paper`.

## The deadline trap

Artifact evaluation is usually a **separate, post-acceptance track** with its own
deadline **weeks after notification** (SIGMOD ARI, ACM/USENIX AE). A plan that
tracks only the *paper* deadline will miss the artifact window — surface the AE
deadline explicitly and route timeline work to `plan-submission`.
