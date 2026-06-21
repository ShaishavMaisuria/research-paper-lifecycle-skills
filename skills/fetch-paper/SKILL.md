---
name: fetch-paper
description: >-
  Fetches a legal open-access copy of a paper from its DOI or arXiv ID —
  resolves through Unpaywall, arXiv PDF/HTML, and the open-access ACM Digital
  Library. Use when the user wants to fetch, download, read, or get the PDF or
  full text of a specific paper. Single polite fetch, transient processing
  only: it never stores paper text in the repo, never bypasses paywalls, and
  never uses shadow libraries. For finding papers by topic or venue, use
  find-papers first; this skill starts from an identifier.
---

# Fetch Paper

Resolves one DOI or arXiv ID to a **legal** open-access copy (PDF URL, arXiv
HTML rendering, landing page) and optionally downloads it for transient
reading. This is the fetch layer that `find-papers`, `literature-review`,
`study-exemplars`, and `draft-related-work` build on.

## When to use

- The user has a DOI, doi.org URL, arXiv ID, or arxiv.org URL and wants the paper.
- Another skill needs full text for a paper it found (lit review, exemplar study).
- The user asks "is there an open-access version of this paper?"
- NOT for topic/title/venue search — run `find-papers` first to get the identifier.

## Inputs

- Exactly one identifier per fetch: a DOI (`10.1145/3589132.3625571`,
  `https://doi.org/...`) or an arXiv ID (`2403.12345`, `arXiv:2403.12345v2`,
  `cs/0309136`, or any arxiv.org URL). arXiv-issued DOIs (`10.48550/arXiv.*`)
  are auto-converted.
- `UNPAYWALL_EMAIL` (or `CONTACT_EMAIL`) env var — a real address; Unpaywall
  rejects placeholders with HTTP 422. The script prompts if unset.

## Process

1. **Resolve the identifier.** Run:

   ```
   python3 scripts/resolve_oa.py <DOI-or-arXiv-ID> --json
   ```

   The script handles everything deterministic: identifier normalization,
   Unpaywall `best_oa_location` lookup, arXiv PDF/HTML URLs, the post-2026
   ACM DL open-access fallback for `10.1145/*` DOIs, rate limiting, 429
   backoff, and response caching under `.cache/fetch-paper/`. Never hand-roll
   these API calls.

2. **Interpret the result** (exit codes: 0 = OA found, 3 = no legal OA copy,
   2 = bad input/config, 1 = network failure):
   - Prefer `html_url` (arXiv HTML) when present — easiest to read directly.
   - Otherwise use `pdf_url`. Read the meaning of `oa_status`, `version`, and
     `license` in [references/oa-sources.md](references/oa-sources.md).
   - `version: submittedVersion` means a preprint — warn the user that the
     published version may differ before they quote or cite page numbers.

3. **Fetch the full text transiently.** Either read the URL directly, or:

   ```
   python3 scripts/resolve_oa.py <ID> --download
   ```

   which saves the PDF to a fresh temp directory (never the repo). Read it,
   extract what the task needs, then delete it. `dl.acm.org` blocks scripted
   downloads — give the user the URL to open in a browser instead.

4. **If exit code is 3 (no legal OA copy):** relay the script's suggestions —
   author homepages / institutional repositories (search via `find-papers`),
   arXiv by title, the user's library access, or emailing the authors. Never
   suggest Sci-Hub, LibGen, or any shadow library, and never try to bypass a
   paywall. Full rules: [references/copyright-and-politeness.md](references/copyright-and-politeness.md).

5. **Process, don't persist.** Quote at most short excerpts in your analysis.
   Never write paper text, abstracts, or the PDF into the repository or any
   committed file. Metadata (DOI, title, BibTeX fields) is always fine.

## Output

- A resolution report (human-readable, or JSON with `--json`): `is_oa`,
  `oa_status`, `license`, `version`, `pdf_url`, `html_url`, `landing_url`,
  `source`, plus notes.
- With `--download`: a transient PDF in a temp directory, path printed to stderr.
- Nothing is ever written into the repository.

## Guardrails

- One identifier per invocation — never loop this script over a list of DOIs
  for bulk harvesting (ACM ToU and arXiv policy both prohibit it). For a
  handful of papers in a session, run it one at a time and let the built-in
  rate limits breathe.
- Legal sources only; transient processing only; no storage, no redistribution.
- Cite the published DOI, not the preprint, when both exist — and verify every
  citation with `verify-citations` before it lands in a bibliography.
- Never submit anything to any system on the user's behalf.

## References

- [references/oa-sources.md](references/oa-sources.md) — Unpaywall fields and
  errors, arXiv URL patterns, ACM DL open access, troubleshooting.
- [references/copyright-and-politeness.md](references/copyright-and-politeness.md)
  — what is safe to keep vs. transient-only, politeness contract.
