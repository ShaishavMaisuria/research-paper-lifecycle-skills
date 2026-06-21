# Placement and citation conventions by community

Where Related Work sits, how long it runs, which citation commands to use,
and how to handle self-citation — per venue family. Conventions drift:
treat this file as the prior, the venue profile (`venues/conferences/<id>.yml`
→ live `cfp_url`) as the check, and 3–5 recent papers from the venue itself
as the ground truth (`find-papers` DBLP toc query or `study-exemplars`).

## Table of contents

1. [How to resolve conventions for a venue](#how-to-resolve-conventions-for-a-venue)
2. [Placement and depth by venue family](#placement-and-depth-by-venue-family)
3. [Citation-command styles](#citation-command-styles)
4. [Citations as nouns vs parentheticals](#citations-as-nouns-vs-parentheticals)
5. [Blind level and self-citation](#blind-level-and-self-citation)
6. [Verifying conventions empirically](#verifying-conventions-empirically)

## How to resolve conventions for a venue

1. Read `venues/conferences/<id>.yml`: `family`, `format.template`,
   `format.documentclass`, `review.blind`, the track's `page_limit` and
   `page_limit_excludes`.
2. Read the referenced `venues/families/<family>.yml` for family-wide rules.
3. **Re-verify against the live `cfp_url`** anything the draft depends on:
   blind level (changes self-citation voice), template (changes citation
   commands), page limit (changes the section's budget). Profiles are
   year-versioned but can still be stale; a wrong blind level produces a
   desk-rejectable draft.
4. **Calibrate length/breadth to the measured exemplar median, not maximal
   coverage.** Read the profile's `exemplar_distribution`: use its
   `related_work` band (`pages` / `refs` / `clusters`) when present, else
   derive a length budget from `refs_per_page` × the section's page share.
   When no on-family distribution is recorded, measure 3–5 recent accepted
   papers via `study-exemplars` (last section below). The family table below
   is a prior, not a target to max out — a Related Work section materially
   longer or denser than the venue's own strong papers reads as survey drift.
5. Confirm placement/length empirically when in doubt (last section below).

## Placement and depth by venue family

| Family (profile) | Typical placement | Typical depth | Notes |
|---|---|---|---|
| ML conferences — `neurips-style` (NeurIPS, ICML, ICLR) | Section 2, **or** penultimate section before Conclusion; both common | Short: 0.3–0.6 page of the 8–9 content pages | Late placement is idiomatic when the method needs no prior-work scaffolding. Extended related work in the appendix is common, but the main body must still position the paper — reviewers are not obliged to read appendices. |
| Vision — CVPR/ICCV-style | Section 2, nearly always | 0.5–1 page | Reviewers expect dense coverage of the last 2–3 years; missing a recent relevant line is a standard reject reason. |
| Data/DB/systems — `acm-sigconf`, `ieee-conf` (SIGMOD, VLDB, ICDE, SIGSPATIAL, KDD, WWW) | Section 2 after Intro, or late (before Conclusion); DB papers use both | 0.5–1 page of 10–12 | Often organized by problem then technique. A comparison table is common in systems papers. SIGSPATIAL-style 4-page short/demo tracks: one paragraph. |
| HCI — `acm-manuscript-chi` (CHI, CSCW, UIST) | Section 2, mandatory and substantial | Long: often 1.5–3 pages, deep engagement | CHI has no hard page limit ("contribution weighed relative to length") but expects Related Work to *synthesize*, not list; engaging HCI theory/qualitative work matters. Skimpy RW is a top CHI rejection theme. |
| Theory / `lncs` (LNCS conferences, theory tracks) | Usually woven into a long Introduction ("Our results" / "Related work" subsection); standalone Section 2 less common | Paragraphs inside intro | Position against known bounds/results precisely; informal characterizations of theorems are punished. |
| Journals — `ieee-journal`, `acm-journal` (TKDE, TODS) | Section 2, comprehensive | 1–2+ pages; survey-grade coverage expected | Journal reviewers check coverage breadth; recency matters less than completeness. |

"Typical" means: what most accepted papers do. The venue's own recent papers
override this table.

## Citation-command styles

Match the template from the venue profile (`format.template` /
`format.documentclass`):

| Template | Bibliography style | Commands to use | Rendered as |
|---|---|---|---|
| `acmart` (ACM: SIGMOD, SIGSPATIAL, KDD, CHI...) | `ACM-Reference-Format` (numeric by default) | `\cite{key}`; `\citet{key}` for textual "Author [n]" (acmart loads natbib) | `[12]` / `Li et al. [12]` |
| `IEEEtran` (ICDE, ICDM, IEEE conferences/journals) | `IEEEtran.bst` numeric | `\cite{key}` | `[12]` |
| `neurips_20XX.sty`, ICML/ICLR styles | natbib author–year by default | `\citep{key}` parenthetical, `\citet{key}` textual — never bare `\cite` ambiguity | `(Li et al., 2018)` / `Li et al. (2018)` |
| `llncs` (Springer LNCS) | `splncs04.bst` numeric | `\cite{key}` | `[12]` |

Rules:

- Use ONE style consistently; `scripts/audit_bib.py` prints a census of
  commands found in the tex (`dominant:` line) — it must match the template.
- Mixed `\citet`/`\citep` in an acmart numeric paper is legal (acmart
  supports natbib) but check what the venue's own papers do.
- Do not hand-format citations ("(Li et al. 2018)" as literal text) — ever.
- BibTeX entries: prefer the publisher DOI version over the arXiv preprint
  when both exist; keep venue names in the style the venue's own
  bibliographies use (DBLP-exported entries are a safe default for CS).

## Citations as nouns vs parentheticals

- Author–year communities (ML): citations may be sentence subjects via
  `\citet`: "Li et al. (2018) propose...". Parenthetical `\citep` for
  support: "...has been studied extensively (Li et al., 2018; Yao et al.,
  2019)."
- Numeric communities (ACM/IEEE/LNCS): "[12] proposes..." as a bare noun is
  accepted in DB/systems writing but considered poor style in others; the
  safe universal form is "Li et al.~[12] propose...". Use `\citeauthor` or
  write the name when the template lacks natbib.
- Never make the reader dereference a number to follow the argument: name
  the work when the sentence depends on *who/what* it is.

## Blind level and self-citation

Read `review.blind` from the venue profile, then re-verify on the live CFP —
this is a desk-reject axis.

- **Double/triple blind** (NeurIPS, ICML, ICLR, CHI, SIGMOD, KDD Research,
  WWW Research; ICDM is triple-blind):
  cite your own prior work in third person, exactly like anyone else's:
  "Chen et al. [9] introduced X" — never "our prior work [9]", "we
  previously showed [9]", or "building on our system [9]". The combination
  "we extend [9]" + [9] sharing your writing style is a classic
  anonymization leak; `preflight-check`/`tailor-to-venue` sweep for it, but
  do not write it in the first place. Unpublished own work that must be
  referenced: anonymize ("Anonymous, under review") only per the venue's
  stated policy.
- **Single blind** (SIGSPATIAL, VLDB, ICDE, EDBT, TKDE-style IEEE journals;
  note TODS is double-blind — always check the profile):
  first-person self-citation is permitted: "we extend our earlier index
  [9] with...". Still keep self-citations proportionate — reviewers notice
  padding.
- Either way, self-citations must pass the same relevance bar as any other
  citation: load-bearing or cut.

## Verifying conventions empirically

When this file and the profile leave doubt (new venue, new track, unusual
template):

1. Enumerate recent accepted papers: `find-papers` with the venue's
   `aliases.dblp_key` toc query (e.g. `toc:db/conf/gis/gis2025.bht:`).
2. Fetch 3–5 OA papers via `fetch-paper` (transient reading only).
3. Record: section number/placement of Related Work, approximate length,
   cluster-paragraph vs laundry-list style, presence of comparison tables,
   citation command style, how authors handle self-citation.
4. Follow the observed majority convention; mention the observation to the
   user in the positioning summary.
