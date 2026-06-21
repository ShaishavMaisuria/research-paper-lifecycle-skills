# Archival hosting and double-blind anonymization

Two things authors get wrong most often: (1) treating a GitHub URL as
"archival," and (2) shipping a review-phase artifact that de-anonymizes them.
Both are checked by `scripts/check_artifact.py`; the why is here.

## GitHub is NOT archival

A GitHub/GitLab/Bitbucket URL is mutable and can vanish — it does **not**
satisfy an "Artifacts Available" badge for the USENIX family, which
**explicitly rejects** GitHub/personal sites for the permanent copy. The
permanent copy must live on an archival host with a persistent identifier.

### Zenodo — extrinsic DOI (concept vs version)

Zenodo mints a DOI for a deposit. The distinction that trips people up:

- **Concept DOI** — always resolves to the *latest* version ("all versions").
- **Version DOI** — points to one *immutable* release.

Artifact committees want a **version DOI** for the **final** submission so they
evaluate exactly what is published. A **concept DOI is acceptable during
evaluation** (you may push fixes), but the final, archived artifact must carry
a version DOI. Pointing reviewers at a concept DOI for the final breaks the
"evaluate exactly what's published" guarantee.

GitHub→Zenodo: enabling the Zenodo–GitHub integration and cutting a GitHub
*release* auto-deposits a snapshot and mints a version DOI.

### Software Heritage — intrinsic SWHID

Software Heritage gives an **intrinsic, content-addressed** identifier
(`swh:1:dir:...`, `swh:1:rev:...`) computed by cryptographic hash — resolvable
without a registry, and able to pin a specific file/directory/revision. The
SWHID format became **ISO/IEC 18670** on 2025-04-23. Use
https://www.softwareheritage.org/save-reference-research-software/ to archive a
public repo and get a SWHID; it integrates with Zenodo/HAL and can emit BibTeX.

**DOI and SWHID are complementary, not interchangeable** — a DOI (extrinsic,
citable, with landing-page metadata) plus a SWHID (intrinsic, tamper-evident,
pins exact content) is the strongest combination. CITATION.cff / codemeta.json
in the repo make both archives emit correct citation metadata.

### Choosing a host

| Need | Use |
|---|---|
| Citable DOI, landing page, large files (50 GB), versioned releases | Zenodo |
| Tamper-evident pin of exact source content, no registry needed | Software Heritage SWHID |
| Datasets specifically | Dryad, FigShare, Zenodo |
| Both citability and content integrity | Zenodo version DOI **+** SWHID |

## Anonymized artifacts for double-blind review

The review-phase artifact must not de-anonymize the authors. Leaks to scrub:

- **git history** — a `.git` directory exposes author names, emails, and the
  origin remote. Ship an anonymized **ZIP** (no `.git`) or proxy through
  Anonymous GitHub.
- **author names / emails / institutional paths** in README, headers,
  docstrings, copyright lines, `setup.py`/`pyproject` author fields.
- **identifying URLs** — personal GitHub/lab pages, internal project names.
- **PDF / artifact-appendix metadata**, acknowledgments, funding/grant numbers,
  and first-person self-citation phrasing (same rules as the paper).

### Anonymous GitHub (anonymous.4open.science)

The de-facto tool (tdurieux/anonymous_github): it proxies a GitHub repo, scrubs
the owner/org/name plus any user-listed identifying terms (names, emails,
institutions, internal project names) across **filenames and file contents**,
auto-refreshes when you push, and has a CLI to produce a **local anonymized
ZIP**. List every identifying term you want scrubbed — the tool only removes
terms you give it plus the obvious repo identity.

Alternative: submit the code as an anonymized ZIP via the conference
supplementary system (NeurIPS wants a single ZIP <100 MB; anonymous URLs for
large data).

### The hand-off at camera-ready

De-anonymization happens at the camera-ready stage (see `prepare-camera-ready`):
restore the real author block, real repo URL, acknowledgments/funding, and PDF
metadata; then deposit the **final** version to Zenodo with a **version DOI**
(and optionally a SWHID) and put that identifier in the camera-ready and the
README.
