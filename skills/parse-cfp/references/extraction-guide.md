# CFP Extraction Guide — field by field

How to turn raw CFP text into a `venues/schema.yml`-conformant profile without
inventing a single fact. Read the matching section before filling each block.

## Table of contents

1. [Ground rules](#1-ground-rules)
2. [Identity and aliases](#2-identity-and-aliases)
3. [Deadlines](#3-deadlines)
4. [Tracks and page limits](#4-tracks-and-page-limits)
5. [Format and template](#5-format-and-template)
6. [Review process](#6-review-process)
7. [Camera-ready](#7-camera-ready)
8. [Provenance block](#8-provenance-block)
9. [Common traps](#9-common-traps)

## 1. Ground rules

- **Extract, never infer numbers.** If a page limit, date, or character limit is
  not literally on a fetched page, the field is `null` plus a note saying it was
  not found. A fabricated page limit can cause someone's desk reject.
- **Quote verbatim for high-stakes prose fields** (`llm_policy`,
  `dual_submission`, per-track page-limit sentences in `notes`). Copy the CFP's
  exact sentence in quotation marks, prefixed `CFP verbatim:`. Short factual
  quotes are fine; never paste whole CFP pages into the profile.
- **One venue, one year per profile.** `id` is year-versioned
  (`sigspatial-2026`), because rules churn annually.
- **Per-track pages beat summary tables.** When the homepage deadline table and
  a track's own submission page disagree, trust the track page and record the
  discrepancy in `notes`.
- **Family fills gaps, marked as such.** Anything inherited from
  `venues/families/<family>.yml` rather than read off the live page must be
  flagged (comment or `confidence: inferred-from-family`).

## 2. Identity and aliases

- `id`: kebab-case venue short name + year (`icde-2026`). Must equal the filename stem.
- `name`: full official name including the ordinal ("34th ACM SIGSPATIAL
  International Conference on...") as printed on the page.
- `family`: pick the closest of `venues/families/` (acm-sigconf, ieee-conf,
  neurips-style, lncs, acm-manuscript-chi, ieee-journal, acm-journal). If none
  fits, leave the best match and note the mismatch.
- `cfp_url`: the page that states the requirements (often
  `.../research-submission.html` or `.../call-for-papers`), not the homepage.
- `aliases`: fill only what you can check key-free:
  - `dblp_key`: query `https://dblp.org/search/venue/api?q=<venue>&format=json`
    (via the fetch script, one call) — the key looks like `conf/gis`. Note that
    DBLP keys often differ from the acronym (SIGSPATIAL → `conf/gis`).
  - `s2_venue` / `crossref_container` / `openalex_source`: copy from the prior
    year's profile when one exists; otherwise leave `null` with a note — do not
    guess. `find-papers` owns the alias table.

## 3. Deadlines

- **Timezone is a fact, not a default.** AoE ("Anywhere on Earth") is common at
  ML venues but NOT universal: SIGSPATIAL 2026 states "11:59 PM Pacific Time".
  Record exactly what the CFP says (`AoE`, `PT`, `ET`, `UTC-12`). If no timezone
  is stated anywhere, set `timezone: AoE` and add a note "timezone not stated
  in CFP — AoE assumed, verify".
- **Abstract registration is its own deadline** at most ML/data venues, usually
  2–7 days before the paper deadline (NeurIPS: 2 days; SIGSPATIAL: 1 week;
  CHI: 1 week). Cue phrases: "abstract registration", "abstract submission",
  "title and abstract due", "mandatory abstract".
- Dates as ISO `YYYY-MM-DD`. "11:59 PM June 5" belongs to June 5 — do not roll
  to the next day.
- Tracks often have different deadline sets; the top-level `deadlines:` block
  describes the main Research track, per-track dates go into each track's `notes`.
- Cue phrases for the rest: "author notification", "camera-ready",
  "rebuttal/author response period", "submission site opens" (NOT a deadline —
  skip it).

## 4. Tracks and page limits

The incl/excl-references distinction is the single highest-stakes fact in the
profile. Patterns seen across real CFPs:

| CFP wording | Encode as |
|---|---|
| "10 pages excluding references" | `page_limit: 10`, `page_limit_excludes: [references]` |
| "up to 2 additional pages after the references for appendices" | add `appendix` to excludes, quote the sentence in `notes` |
| "4 pages including references" | `page_limit: 4`, `page_limit_excludes: []` |
| "9 content pages; references, appendices and the checklist do not count" | `page_limit: 9`, `page_limit_excludes: [references, appendix, checklist]` |
| "12 pages plus unlimited pages for citations" | `page_limit: 12`, `page_limit_excludes: [references]` |
| "no strict page limit; contribution weighed relative to length" (CHI) | `page_limit: null`, explain in `notes` |

Rules:

- One `tracks:` entry per track (Research, Applications/Industry, Demo, Short,
  Vision, Experiments/Benchmarks...). Workshops are NOT tracks — skip them.
- Always quote the limit sentence verbatim inside `notes`, plus track-specific
  deadlines and submission instances (e.g. separate EasyChair conference codes).
- Watch for length-dependent rules ("5 to 10 pages"), poster-conversion options,
  and title-tag requirements (e.g. SIGSPATIAL experiment papers need an
  "[Experiment]" suffix in the title) — all go into `notes`.
- Supplementary material rules (separate ZIP, size caps, "reviewers are not
  required to read appendices") also belong in the relevant track's `notes`.

## 5. Format and template

- `template`: one of `acmart | IEEEtran | neurips | llncs | chi-manuscript |
  aaai` (or the style file the CFP names).
- `documentclass`: the exact invocation. CFPs rarely print it — derive from the
  family table in [templates-and-systems.md](templates-and-systems.md), adding
  `review,anonymous` options only when the venue is double/triple-blind, and
  comment that the invocation is family-derived. If the CFP names a versioned
  style file (`neurips_2026.sty`, "AAAI-26 author kit"), capture that exact name.
- `abstract_words`: only if the CFP states a range (LNCS: 150–250 words).
  Otherwise `null`.
- `keywords`: `ccs-concepts` (ACM), `ieee-index-terms` (IEEE), `lncs-keywords`
  (Springer, usually 3–6), or `none`.
- `required_sections`: machine-checkable extras that cause desk rejects when
  missing — e.g. `neurips-checklist`, `icml-impact-statement`,
  `ai-use-acknowledgement` (ICDE), `coi-declaration` (ICDE), `ccs-concepts`,
  `acm-reference-format`. Only list what the CFP (or family) actually requires.

## 6. Review process

- `blind` — map the CFP's wording, do not assume from the publisher:
  - "names and affiliations should be listed" / "single-blind" → `single`
  - "anonymized" / "remove author names" / "double-blind" → `double`
  - "authors do not know reviewers, reviewers do not know authors, and the
    PC/AC identities are also hidden" / "triple-blind" (ICDM) → `triple`
- `submission_system` + `submission_url`: detect from links on the page — see
  the domain table in [templates-and-systems.md](templates-and-systems.md).
  Capture the exact URL including the conference code
  (`easychair.org/conferences/?conf=acmsigspatial2026`).
- `rebuttal_format`: `none | openreview-thread | one-page-pdf |
  revise-and-resubmit` (taxonomy and examples in templates-and-systems.md).
  `rebuttal_limit` is the stated budget ("10,000 characters per review",
  "1 page PDF"). If the CFP never mentions a rebuttal, `none` + note.
- `llm_policy`: VERBATIM. This is a compliance field — paraphrasing can flip
  its meaning. Typical shapes: ACM's "generative AI tools may not be listed as
  authors... use must be fully disclosed"; NeurIPS's "important, original, or
  non-standard use must be described"; ICDE's mandatory AI-Generated Content
  Acknowledgement section. If absent: `null` + note "no LLM/AI-use policy found
  on <urls checked>".
- `dual_submission`: quote the originality/concurrent-submission sentence.
  Watch for extras: resubmission embargoes (ICDE: 1 year), too-similar
  concurrent-submission rules (NeurIPS: overlapping simultaneous submissions
  risk mutual rejection), max-papers-per-author caps.

## 7. Camera-ready

- `rail`: `acm-taps` (ACM venues), `ieee-pdfexpress` (IEEE), `springer` (LNCS),
  `openreview-direct` (NeurIPS/ICML/ICLR). Details per rail in
  templates-and-systems.md. Venues do leave rails (FAccT 2026 left TAPS), so
  prefer what the CFP/author-kit page says over the family default.
- `extra_pages`: e.g. NeurIPS "+1 content page allowed at camera-ready". Only
  if stated.
- `requirements`: ordered, actionable checklist items specific to this venue
  (registration mandated for publication, in-person presentation/no-show
  policy, per-track camera-ready dates, file-naming conventions).

## 8. Provenance block

Mandatory. Without it the profile fails `tools/validate_venues.py`.

```yaml
verified:
  date: <today, YYYY-MM-DD>
  source_urls:        # EVERY page you fetched, with a comment on what it gave you
    - https://...
  confidence: verified-live   # only when every critical fact was read off live pages
```

- `verified-live`: deadlines, page limits, blind level, and submission system
  all read from pages fetched today.
- `inferred-from-family`: one or more critical facts came from the family file.
- `needs-verification`: anything user-pasted, cached >1 day, or gap-ridden.

## 9. Common traps

- **Wrong year.** Old CFPs stay online at near-identical URLs. Confirm the year
  in the page heading and dates before extracting; if the user gave a stale
  year's URL, say so and ask for or locate the current one.
- **Deadline table vs track page disagreement.** Track page wins; note the
  conflict.
- **Extended deadlines render as two dates.** Sites strike through the old
  date and append the new one; extracted text shows them concatenated
  ("Friday, May 22nd, 2026 Friday, May 29th, 2026"). Take the LATER date and
  note the extension. If unsure which is current, check the page with `--html`
  for `<s>`/`<del>`/strikethrough markup.
- **"Submission site opens" mistaken for a deadline.** Skip openings.
- **Workshop CFPs on the same site.** Main-conference tracks only, unless the
  user asked for a workshop (then make a separate profile).
- **JS-rendered pages** (some OpenReview-hosted CFPs): the fetch script warns
  when it extracts almost no text. Ask the user to paste the page content;
  mark the profile `needs-verification`.
- **PDF CFPs**: the fetch script saves the file and exits with code 3 — read
  the saved PDF directly.
- **Camera-ready limits differ from submission limits** (+1/+2 pages). Never
  merge them into one number.
- **Midnight arithmetic**: "23:59 AoE" = UTC-12; do not convert dates across
  days. Store what is written plus the stated timezone.
- **Anonymization scope**: some venues extend blinding to supplementary
  material and linked repos (CHI, NeurIPS). Quote that into the track or
  review notes — `preflight-check` consumes it.
