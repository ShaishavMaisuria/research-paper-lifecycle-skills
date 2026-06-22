---
name: parse-cfp
description: Parses a conference Call for Papers (CFP) URL into a machine-checkable requirements card - deadlines with timezone (AoE vs local), per-track page limits including/excluding references, single/double/triple-blind level, exact LaTeX template invocation, LLM/AI-use policy, rebuttal format, and submission system (OpenReview, CMT, EasyChair, HotCRP, PCS) - emitted as a year-versioned venue-profile YAML conforming to venues/schema.yml. Use when the user shares a CFP or author-instructions URL, asks what a venue's submission requirements, deadlines, page limits, or anonymity rules are, or wants a venue profile under venues/conferences/ created or refreshed for a new submission cycle.
---

# Parse CFP

Turn a live Call for Papers into the machine-readable venue profile that the
rest of this repo runs on. Output is a `venues/conferences/<venue>-<year>.yml`
file conforming to `venues/schema.yml`, plus a human-readable requirements card.
Downstream consumers: `preflight-check`, `tailor-to-venue`, `write-rebuttal`,
`prepare-camera-ready`, `select-venue`.

## When to use

- The user pastes a CFP, author-guidelines, or submission-instructions URL.
- "What are the requirements / deadlines / page limits for VENUE YEAR?"
- A profile in `venues/conferences/` is missing or a year out of date.

## Inputs

- A CFP URL. If the user only names a venue, check
  `venues/conferences/<venue>-<year>.yml` for a `cfp_url` first; an older
  year's profile usually links the venue website where the new CFP lives.
- `venues/schema.yml` — read it before writing the profile; it defines every
  field and the mandatory `verified:` provenance block.
- The matching `venues/families/<family>.yml` for family-level defaults.
- `CONTACT_EMAIL` env var (used in the polite fetch User-Agent; the script
  prompts if unset).

## Process

1. **Scope one venue + one year.** Read `venues/schema.yml`. If a profile for
   this venue-year already exists, treat it as hints to re-verify, never as
   ground truth.

2. **Fetch the CFP page.** Run:

   ```
   python3 scripts/fetch_cfp.py "<cfp-url>"
   ```

   The script fetches ONE page per invocation, rate-limits to 1 request/second
   per host, backs off exponentially on HTTP 429, caches under `.cache/`
   (gitignored) for 24h, and prints readable text with link targets as `[url]`.
   It exits nonzero with a clear message on failure. Then fetch the handful of
   follow-up pages you actually need — per-track submission pages, the
   deadlines page, the camera-ready/author-kit page — one invocation each,
   never a site crawl.
   - Exit code 3 = non-HTML content (a PDF CFP, a JSON API response); the
     body is saved under `.cache/` — read that file directly.
   - "very little text extracted" warning = JavaScript-rendered page; ask the
     user to paste the page text and mark the profile `needs-verification`.
     Never fill gaps from memory.

3. **Verify the year.** Confirm the page heading and dates match the requested
   year before extracting — stale CFPs survive at near-identical URLs. Wrong
   year: tell the user and locate the current page.

4. **Extract every schema field** following
   [references/extraction-guide.md](references/extraction-guide.md). The
   non-negotiables:
   - Numbers (page limits, char limits, dates) only from fetched text; missing
     fact = `null` + an explanatory note. Never infer, never recall.
   - Page limits must capture what is EXCLUDED (references? appendix?
     checklist?) with the CFP's sentence quoted verbatim in the track `notes`.
   - Deadlines: record the stated timezone — AoE is common, not universal
     (SIGSPATIAL uses Pacific Time). Abstract registration is a separate,
     earlier deadline at most venues.
   - `llm_policy` and `dual_submission`: verbatim quotes, never paraphrased.

5. **Normalize** the template invocation, submission system, rebuttal format,
   and camera-ready rail using
   [references/templates-and-systems.md](references/templates-and-systems.md).
   Derive `\documentclass` options from the family table (add
   `review,anonymous` only for double/triple-blind venues) and comment when an
   invocation is family-derived rather than printed in the CFP.

6. **Emit the YAML** to `venues/conferences/<venue>-<year>.yml`:
   - `id` equals the filename stem; `family` references an existing family file.
   - Fill the mandatory `verified:` block — today's date, every URL fetched
     (with a comment on which facts each supplied), and an honest
     `confidence:` (`verified-live` only if all critical facts came off live
     pages today).

7. **Validate.** Run `python3 tools/validate_venues.py` from the repo root
   (needs PyYAML; if unavailable, check the file manually against
   `venues/schema.yml` field by field).

8. **Present the requirements card** to the user: a short table of deadlines
   (with timezone), per-track limits with their exclusions, blind level,
   template invocation, submission URL, rebuttal format, and LLM policy. End
   with the verification notice: *"Profile extracted from <cfp_url> on <date>.
   Re-verify deadlines and page limits against the live CFP before submitting —
   CFPs change mid-cycle and a stale limit can cause a desk reject."*

## Worked mini-example

User pastes `https://sigspatial2026.sigspatial.org/research-submission.html`.
After fetching, the Research-track section reads: *"papers are limited to 10
pages (excluding references), with up to 2 additional pages after the references
to be used for appendices"*, deadlines are stated as *"11:59 PM Pacific Time"*,
and the submission link points at `easychair.org/conferences/?conf=acmsigspatial2026`.
That extracts to:

```yaml
id: sigspatial-2026
deadlines:
  abstract: 2026-05-29
  paper: 2026-06-05
  timezone: PT          # CFP says "Pacific Time", NOT AoE — recorded verbatim
tracks:
  - name: Research
    page_limit: 10
    page_limit_excludes: [references, appendix]
    notes: >
      CFP verbatim: "papers are limited to 10 pages (excluding references),
      with up to 2 additional pages after the references ... for appendices."
review:
  blind: single         # CFP lists author names — single, not double
  submission_system: easychair
verified:
  date: 2026-06-21
  source_urls:
    - https://sigspatial2026.sigspatial.org/research-submission.html  # limits, deadlines, blind
  confidence: verified-live
```

Two traps this example surfaces and the guide handles: the timezone is Pacific,
not the AoE default, and the page limit excludes both references AND the
appendix — encoded explicitly so `preflight-check` can enforce it. The page
heading is confirmed to say 2026 before any of this is extracted.

## Output

- `venues/conferences/<venue>-<year>.yml` — schema-conformant, year-versioned,
  with provenance.
- An inline requirements-card summary with the re-verify warning.

## Guardrails

- Never fabricate a deadline, limit, or policy. `null` + note beats a guess.
- Quote LLM-use and dual-submission policies verbatim; paraphrase can invert
  compliance meaning.
- GET-only. Never log in to, register with, or submit to any submission system
  on the user's behalf.
- Never fabricate citations. This skill emits venue metadata only; if a paper
  reference is ever needed downstream, route it through `verify-citations`.
- One page per script invocation; no bulk crawling. The cache lives under
  `.cache/` and stays out of git — do not commit fetched CFP text to the repo.
- Always include the re-verify-against-live-CFP notice in the final answer.

## Source verification (mandatory)

This skill *originates* venue facts, so source verification is mandatory without exception:

- The venue is the **user's choice**; build its rules **on demand**, never from memory or a prior year.
- **Search the web for the live CFP / author-instructions page and read the primary source** — never state a fact from a search snippet you didn't open, and never from a deadline aggregator without confirming on the official site.
- **Double-check every desk-reject-class fact** (deadline, page limit + exclusions, blind level, template, submission system) against a second source; if sources disagree, surface the conflict — do not pick silently.
- **Record a clickable reference link and the date for every fact** in the profile's `verified.source_urls`; set `confidence` to `verified-live`/`corroborated` only when sourced, else `needs-verification`. A fact with no link is emitted as unverified, never asserted.

## Bundled files

- [references/extraction-guide.md](references/extraction-guide.md) —
  field-by-field extraction rules, cue phrases, and the trap list.
- [references/templates-and-systems.md](references/templates-and-systems.md) —
  template invocations by family, submission-system URL patterns, rebuttal
  taxonomy, camera-ready rails.
- `scripts/fetch_cfp.py` — polite single-page fetcher (run it; do not reimplement
  fetching by hand).
