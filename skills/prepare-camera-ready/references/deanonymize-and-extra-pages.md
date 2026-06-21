# De-anonymization checklist and camera-ready +page rules

For papers accepted at blind-review venues, de-anonymization comes FIRST —
every rights form (ACM eRights, IEEE eCF) requires the exact final title
and author list, and rights-form metadata overrides the source in
production. Then fit the paper to the camera-ready page budget.

## Table of contents

1. [Order of operations](#1-order-of-operations)
2. [De-anonymization checklist](#2-de-anonymization-checklist)
3. [What NOT to change](#3-what-not-to-change)
4. [Camera-ready +page rules by family](#4-camera-ready-page-rules-by-family)
5. [Using the extra space well](#5-using-the-extra-space-well)

## 1. Order of operations

1. Settle the final author list and order with all coauthors (changes after
   submission are restricted: NeurIPS allows reorder but no add/remove;
   ACM/IEEE route changes through chairs).
2. Settle the final title (rebuttal-promised tweaks happen NOW).
3. De-anonymize the source (checklist below).
4. Only then open eRights / eCF — the forms are effectively one-shot.
5. Fit to the page budget; run `python3 scripts/check_camera_ready.py` after
   every editing pass.

## 2. De-anonymization checklist

Source-level (the lint script checks most of these):

- [ ] Drop submission-mode options: `review`, `anonymous` (acmart),
      `[submission]` (AAAI kit); switch NeurIPS-style packages to
      `\usepackage[final]{<venue>_<year>}` with the CURRENT year's file.
- [ ] Restore the real author block: names, affiliations, emails — and
      ORCIDs where the class supports them (`\orcid{}` in acmart; ACM
      requires ORCIDs for all authors anyway).
- [ ] Remove "Anonymous Author(s)" / "Anonymous Institution" placeholders
      everywhere, including `\author{}`, headers, and supplementary files.
- [ ] Restore acknowledgments: people, funding agencies, grant numbers
      (`\begin{acks}` in acmart). These were removed/blinded at submission;
      funders require them back.
- [ ] Replace anonymized artifact links (`anonymous.4open.science`,
      anonymized GitHub mirrors) with the real repository/dataset URLs —
      and make those repos public before the paper appears.
- [ ] Un-blind self-citations: rewrite "the authors of [12] showed" back to
      "we showed [12]" where it reads better, and restore any
      citations-to-own-work that were suppressed or anonymized ("Anonymous,
      2025" placeholder entries in the .bib). New/changed entries go
      through `verify-citations`.
- [ ] Restore PDF metadata: `pdfauthor={...}` in hyperref; clear any
      "anonymous" strings from `pdftitle`/`pdfsubject`.
- [ ] Restore camera-ready-only sections the venue requires (e.g. IEEE
      AI-content acknowledgement, artifact/data availability statements).
- [ ] Sweep supplementary material and appendices for all of the above —
      blinding leftovers hide there.

Cross-checks:

- [ ] Title and author list/order in the source == what will go on the
      rights form == what is in the submission system metadata.
- [ ] Every coauthor has seen the final author order and affiliations
      (affiliations may have changed since submission — use the affiliation
      where the work was done, per venue norms).

## 3. What NOT to change

Camera-ready is not a second revision cycle:

- No new claims, results, or sections beyond what reviewers/shepherds
  approved; venues may run camera-ready checks against the accepted
  version.
- Do not "fix" the title or abstract in ways that diverge from the rights
  form after it is filed.
- Do not silently drop limitations or required statements (checklists,
  impact/ethics statements stay in, with final answers).
- Template tampering (margins, spacing, font tricks) to fit the budget is
  desk-reject-grade at submission and production-bounce-grade here.

## 4. Camera-ready +page rules by family

NEVER assume an allowance: rules are per venue per year. The table below is
the verified state of the bundled profiles (2026-06-11) — re-verify against
the live camera-ready instructions before cutting or paying for pages.

| Family / venue | Camera-ready page rule |
|---|---|
| NeurIPS-style (NeurIPS, ICML, ICLR) | **+1 content page** family-wide (NeurIPS 2026: 9→10; ICML 2026: 8→9; ICLR 2026: 9→10). References/appendix/checklist stay excluded. |
| ACM sigconf (SIGSPATIAL, SIGMOD, KDD, WWW...) | **Per conference** — some sell/grant +1/+2, many (e.g. SIGSPATIAL 2026) state none. Check `camera_ready.extra_pages` in the profile, then the venue page. |
| CHI / acm-manuscript | No fixed "+N": TAPS renders the final 2-column PDF; "contribution weighed relative to length" persists. Follow the acceptance/AC instructions. |
| IEEE conferences (ICDE, ICDM, BigData...) | **Per conference**; many sell +1/+2 overlength pages at a fee, some (ICDE 2026) allow none — final papers keep the submission limit. |
| AAAI | Camera-ready gets 7 pages + references AND acknowledgments; up to **2 extra technical pages purchasable at $300/page** (AAAI-26). |
| LNCS / Springer | Stay within the accepted length in LNCS format; no standard purchase scheme — per venue. |

Where the profile says `extra_pages: null`, the script prints "not stated —
never assume"; treat the submission limit as the budget until the venue
says otherwise.

## 5. Using the extra space well

When a +page allowance exists, spend it in review-driven order:

1. Changes promised in the rebuttal/discussion (reviewers check).
2. Restored acknowledgments/funding and de-anonymized artifact links
   (they consume space the blinded version did not).
3. Clarifications reviewers asked for; expanded figures/tables that were
   cramped.
4. Only then: new related work (verified via `verify-citations`) or extra
   analysis — and never new claims.

If the paper now OVERFLOWS (rights block, author block, and
acknowledgments all add lines): cut from appendices first, compress figure
whitespace, tighten prose — never the template.
