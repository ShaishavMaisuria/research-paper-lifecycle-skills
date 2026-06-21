# Venue norms: abstract length, metadata constraints, and abstract registration

Family-level norms the skill applies when drafting. Profiles in `venues/`
are the per-venue source of truth; this file explains the patterns. Every
specific number below must still be re-verified against the live CFP
(`cfp_url` in the profile) before the user relies on it.

## Contents

- [Length norms by family](#length-norms-by-family)
- [The abstract is metadata](#the-abstract-is-metadata)
- [Abstract registration: a separate deadline](#abstract-registration-a-separate-deadline)
- [What gets registered](#what-gets-registered)
- [Placeholder and divergence policies](#placeholder-and-divergence-policies)
- [Title norms](#title-norms)

## Length norms by family

| Family (`venues/families/`) | `abstract_words` | Working norm |
|---|---|---|
| `lncs` | **[150, 250] — mandated** | Springer LaTeX template: "150--250 words"; 3-6 keywords |
| `acm-sigconf`, `acm-journal`, `acm-manuscript-chi` | null | 150-250 conventional; CCS Concepts + keywords required |
| `ieee-conf`, `ieee-journal` | null | 150-250 conventional; Index Terms after the abstract |
| `neurips-style` | null | "one paragraph" — no published word count; **do not invent one** |

When a profile's `format.abstract_words` is null, present 150-250 as a
*convention*, never as a venue rule. If the user asks "what is the limit",
the honest answer for most venues is "none published — here is the
convention, and here is the live CFP to confirm".

## The abstract is metadata

The abstract is reproduced outside the PDF — in OpenReview/EasyChair/CMT
forms (plain text), ACM TAPS HTML, IEEE Xplore, DBLP-linked landing pages,
and review-assignment tooling. Consequences (all linted by
`scripts/abstract_check.py`):

- **No `\cite`** — renders as a raw key or dangling number outside the PDF.
- **No `\ref`/`\autoref`** — dangling outside the PDF.
- **Avoid math** — `$...$` breaks or uglifies in HTML/metadata renderings;
  write it in words.
- **Self-contained prose** — no "see Section 3", no undefined acronyms.
- **Plain-text twin**: whatever goes in the submission form must match the
  PDF abstract; prepare the form version (LaTeX stripped) alongside.
- **acmart ordering**: the `abstract` environment must come BEFORE
  `\maketitle` or acmart drops/mis-typesets it.

## Abstract registration: a separate deadline

Most ML/data venues require registering the title + abstract + authors +
topics + conflicts days before the paper PDF. Treat it as its own
deliverable with its own deadline. Verified examples (from profiles, all
re-verifiable on each `cfp_url`):

| Venue | Abstract | Paper | Gap | Timezone |
|---|---|---|---|---|
| NeurIPS 2026 | 2026-05-04 | 2026-05-06 | 2 days | AoE — mandatory registration |
| SIGSPATIAL 2026 (Research) | 2026-05-29 | 2026-06-05 | 7 days | **PT, not AoE** |
| CHI 2026 | 2025-09-04 | 2025-09-11 | 7 days | AoE (metadata registration) |
| ICML 2026 | 2026-01-23 | (per CFP) | days | AoE |
| KDD 2026 (cycle 2) | 2026-02-01 | (per CFP) | days | AoE |

Notes:

- Timezones differ — SIGSPATIAL uses 11:59 PM **Pacific**, most others AoE.
  Always print the timezone next to the date; never assume AoE.
- Some venues have **no** abstract deadline (ICDE research, EDBT, journals);
  the registration card then doubles as a submission-form prep sheet.
- Per-track deadlines differ at multi-track venues (SIGSPATIAL tracks span
  three weeks of deadlines) — pass `--track` to the script.

## What gets registered

The form at registration time typically wants, and the card
(`scripts/abstract_registration.py`) therefore assembles:

1. **Title** — real, near-final (see divergence policies below).
2. **Abstract** — real text; the paper can refine it, not replace it.
3. **Author list** — complete and ordered; many venues freeze the author
   list at the abstract or paper deadline (CVPR required completed
   OpenReview profiles by the abstract deadline). Check the CFP wording.
4. **Topics / subject areas** — from the form's own taxonomy; at
   OpenReview venues these drive reviewer assignment.
5. **Conflicts of interest** — co-authors within the venue's window
   (commonly 3-5 years), advisors/advisees (usually permanent), current
   institution(s), financial/personal. Enumerate from the user's recent
   papers and lab roster; the venue form defines the authoritative
   categories and window.

## Placeholder and divergence policies

Registering junk to hold a slot is penalized:

- KDD 2026 CFP: "Placeholder or dummy abstracts are forbidden. Large
  changes to the abstract may result in a desk rejection."
- AAAI 2026: placeholder titles/abstracts are deleted at the abstract
  deadline.
- General rule: register text you would defend, then only *refine* it in
  the final PDF. The linter flags TODO/TBD/XXX/lorem-ipsum as RISK.

## Title norms

- Working titles registered at the abstract deadline should be near-final;
  big retitles between registration and submission can trip
  placeholder/divergence policies and confuse reviewer bidding.
- Some venues mandate title markers per track — e.g. SIGSPATIAL
  Experiment/Benchmark papers carry an "[Experiment]"-style suffix in the
  title. Check the track notes in the venue profile and the CFP.
- Double-blind venues: the registered title and abstract must not leak
  identity (system names already public under the group's brand, grant
  numbers, "our prior work").
