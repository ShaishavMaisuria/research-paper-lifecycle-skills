# Venue-profile walkthrough — field by field

How to fill every block of a `venues/conferences/<venue>-<year>.yml` profile
from the live CFP. Read alongside `venues/schema.yml` (the contract) and an
exemplar like `venues/conferences/sigspatial-2026.yml` (the house style).

## Contents

- [Rule zero](#rule-zero)
- [1. Pick the family](#1-pick-the-family)
- [2. Identity fields](#2-identity-fields)
- [3. The alias table](#3-the-alias-table)
- [4. Deadlines](#4-deadlines)
- [5. Tracks and page limits](#5-tracks-and-page-limits)
- [6. Format block](#6-format-block)
- [7. Review block](#7-review-block)
- [8. Camera-ready rail](#8-camera-ready-rail)
- [9. The verified block](#9-the-verified-block)
- [10. The trap list](#10-the-trap-list)

## Rule zero

Every number, date, and policy comes from text you fetched this session.
A missing fact is `null` plus a note saying where you looked. Training-data
recall about a venue is a hypothesis to verify, never a source. When the CFP
and your expectation disagree, the CFP wins.

## 1. Pick the family

`family:` must name an existing file in `venues/families/` — the family
carries the rules shared across sibling venues so the profile only records
deltas. If no family fits, the family file is a separate, prior contribution.

| Family | Template | Typical members | Tells in the CFP |
|---|---|---|---|
| `acm-sigconf` | `acmart`, 2-column `sigconf` | SIGSPATIAL, SIGMOD, KDD, WWW | "ACM proceedings template", CCS Concepts, TAPS |
| `acm-manuscript-chi` | `acmart`, 1-column `manuscript` | CHI, CSCW, UIST | "single-column manuscript", PCS, Revise & Resubmit |
| `acm-journal` | `acmart` journal | TODS, TIST | ScholarOne/ManuscriptCentral, revision rounds |
| `ieee-conf` | `IEEEtran` 2-column | ICDE, ICDM, ICME | "IEEE template", PDF eXpress, CMT |
| `ieee-journal` | `IEEEtran` journal | TKDE | ScholarOne, double-column page counts incl. bios |
| `neurips-style` | year-versioned `.sty` | NeurIPS, ICML, ICLR | OpenReview, content-page limit, paper checklist |
| `lncs` | `llncs.cls` | Springer conference proceedings | "LNCS format", 150–250-word abstract, Springer guidelines |

Family supplies defaults (documentclass shape, keywords style, camera-ready
rail); the conference file overrides them only where the CFP differs. Comment
any value you inherited from the family rather than read off the CFP.

## 2. Identity fields

- `id` — kebab-case, equals the filename stem, year-suffixed for conferences
  (`mdm-2026`), bare for rolling journals (`tkde`).
- `name` — the full official name as the CFP states it, ordinal and all:
  `ACM SIGSPATIAL 2026 (34th ACM SIGSPATIAL International Conference on ...)`.
- `cfp_url` — the page future agents must re-verify against. Prefer the
  per-track submission page over the homepage; it is where the limits live.
- `website` — the conference homepage.

## 3. The alias table

The same venue has different names in every API — the alias table is what
makes the profile usable by `find-papers` and `select-venue`. One polite
lookup per field; record nulls honestly with a "searched on <date>, not
found" comment.

- `dblp_key` — form `conf/<key>` or `journals/<key>`. Look up with ONE call:
  `https://dblp.org/search/venue/api?q=<venue>&format=json` and read the key
  out of the hit's URL. Keys are often non-obvious: SIGSPATIAL is `conf/gis`.
  Sanity-check with a toc query (`q=toc:db/conf/<key>/<key><year>.bht:` on
  `dblp.org/search/publ/api`) — it should return that year's paper list.
- `s2_venue` — Semantic Scholar's venue string, which differs from DBLP's
  (SIGSPATIAL is `SIGSPATIAL/GIS` there). Verify with a single
  `/graph/v1/paper/search/bulk?query=*&venue=<string>&year=<year>` call if
  needed; unauthenticated S2 throttles hard, so back off on 429 and do not
  retry in a loop.
- `crossref_container` — a substring that matches the proceedings
  `container-title` across years. ACM phrasings vary by year ("Proceedings of
  the 31st ACM International Conference on ..."), so choose the stable middle
  of the title, not the ordinal.
- `openalex_source` — frequently absent for ACM conference proceedings
  (OpenAlex often has `primary_location.source = null` for them); `null` with
  a comment is the normal, honest answer.

## 4. Deadlines

- ISO dates (`YYYY-MM-DD`) in the profile; the prose timezone goes in
  `deadlines.timezone` exactly as the CFP states it. **AoE is common, not
  universal** — SIGSPATIAL uses 11:59 PM Pacific Time. Recording AoE for a
  PT venue silently moves the deadline by almost a day.
- `abstract` is the registration deadline, separate from and earlier than
  `paper` at most ML and data venues (NeurIPS ~2 days, SIGSPATIAL ~1 week,
  CHI ~1 week). If the CFP lists only one date, set `abstract: null` and say
  so in a comment.
- Tracks with different dates: the top-level `deadlines:` block carries the
  flagship research track; per-track dates go in each track's `notes`.
- Rolling journals: all-null deadlines with a comment is correct.

## 5. Tracks and page limits

One entry per track the CFP defines (Research, Industry/Applications, Short,
Demo, Vision...). For each:

- `page_limit` — integer, exactly as printed.
- `page_limit_excludes` — what does NOT count against the limit, drawn from
  `[references, appendix, checklist, bios, acknowledgments,
  impact-statement]`. Use `[]` only when the CFP explicitly says the limit
  includes everything (ICDM-style "including bibliography and appendices"),
  and say so in `notes`. If the CFP is silent on incl/excl, leave the key
  with `[]`, and flag the ambiguity in `notes` as unverified — this
  distinction is the single most common desk-reject cause.
- `notes` — the CFP's limit sentence quoted VERBATIM, plus track-specific
  deadlines and submission-system instance if they differ.

## 6. Format block

- `template` — the artifact name: `acmart`, `IEEEtran`, `neurips` (style
  file is year-versioned, e.g. `neurips_2026.sty` — record the exact name in
  a comment), `llncs`, `chi-manuscript`.
- `documentclass` — the exact invocation, escaped for YAML:
  `"\\documentclass[sigconf,review,anonymous]{acmart}"`. Include
  `review,anonymous` only for double/triple-blind venues; the validator
  cross-checks this against `review.blind`. If the CFP prints no invocation,
  derive it from the family and comment that it is family-derived.
- `abstract_words` — `[min, max]` only if the CFP mandates it (LNCS:
  150–250); otherwise `null`.
- `keywords` — `ccs-concepts` (ACM), `ieee-index-terms`, `lncs-keywords`,
  or `none`.
- `required_sections` — machine-checkable extras whose absence desk-rejects:
  `neurips-checklist`, `icml-impact-statement`, `ai-use-acknowledgement`
  (ICDE), `coi-declaration`.

## 7. Review block

- `blind` — `single` | `double` | `triple`, from the CFP's own sentence
  (quote it in a comment). Do not assume double-blind: SIGSPATIAL and TKDE
  are single-blind, ICDM is triple-blind.
- `submission_system` + `submission_url` — read the actual link off the CFP.
  Typical mapping (verify per venue, systems change): OpenReview —
  NeurIPS/ICML/ICLR; CMT — ICDE and many IEEE events; EasyChair —
  SIGSPATIAL and the conference long tail; HotCRP — USENIX/SIGCOMM/SIGPLAN/
  security venues; PCS — CHI and the SIGCHI family; ScholarOne — IEEE/ACM
  journals.
- `rebuttal_format` — `none` | `openreview-thread` (with `rebuttal_limit`
  like "10000 chars per review") | `one-page-pdf` (CVPR-style strict) |
  `revise-and-resubmit` (CHI 5-week R&R, journal revision rounds). No
  rebuttal mentioned in the CFP → `none` plus a "not mentioned" comment.
- `llm_policy`, `dual_submission` — VERBATIM quotes inside a `>` block
  scalar, attributed ("CFP verbatim: ..."). Paraphrasing a compliance policy
  can invert its meaning; an absent policy is `null` + "no policy found on
  <pages checked>".

## 8. Camera-ready rail

- `rail` — `acm-taps` (eRights → ORCID for all authors → DOI block → upload
  LaTeX/Word SOURCE to TAPS), `ieee-pdfexpress` (PDF eXpress validation with
  the conference ID → file-naming convention → eCF copyright form →
  registration/no-show policy), `springer`, `openreview-direct`, or
  `scholarone-final-files`.
- `extra_pages` — only if stated (NeurIPS: +1 content page at camera-ready).
- `requirements` — ordered, venue-specific checklist items beyond the family
  defaults (e.g. track-specific camera-ready deadlines, mandatory author
  registration, title-suffix conventions).
- Venues do leave their family's rail (FAccT left TAPS) — trust the CFP's
  camera-ready page over the family default and note the deviation.

## 9. The verified block

The merge gate. Profiles without honest provenance are not merged.

- `date` — today, the day you actually checked.
- `source_urls` — every page facts came from, each annotated with which
  facts it supplied (`# page limits, dates, blind level`). Include API
  lookup URLs used for aliases.
- `confidence`:
  - `verified-live` — every critical fact (deadlines, limits, blind level,
    system) read off live pages today.
  - `inferred-from-family` — some normative fields derived from the family
    file rather than printed in this CFP; comment which.
  - `needs-verification` — anything came from pasted text, a PDF of unknown
    vintage, a stale page, or could not be checked.

When refreshing an existing profile, update `verified:` and explicitly tell
the user what changed (old → new) — silent rewrites hide regressions.

## 10. The trap list

1. **Stale CFP at a near-identical URL.** Sites keep last year's pages live.
   Match the page's stated year and conference dates before extracting.
2. **Timezone.** "11:59 PM" without AoE is a venue-local claim — find the
   timezone sentence; never default to AoE.
3. **Incl/excl references.** "10 pages" means different things at SIGSPATIAL
   (excl. refs) and ICDM (incl. everything). Quote the sentence.
4. **Abstract-registration deadline** missed because it only appears in the
   dates table, not the prose.
5. **Year-versioned style files** (`neurips_2026.sty`): recording last
   year's file name fails template checks downstream.
6. **`anonymous` flag mismatch** with the blind level — the validator warns;
   fix the data, not the warning.
7. **Tracks hide on separate pages.** Fetch each track's page (one call
   each); the research-track page rarely states demo-track limits.
8. **Per-track submission systems.** Same venue, different EasyChair
   instances per track — record them in track `notes`.
9. **Mid-cycle CFP edits.** Deadlines slip and limits get amended; that is
   why `verified.date` exists and why every consumer must re-verify.
10. **Copy-forward contamination.** When seeding from last year's profile,
    treat every copied value as unverified until re-checked live; do not let
    old verbatim quotes survive into the new file unread.
