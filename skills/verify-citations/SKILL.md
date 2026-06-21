---
name: verify-citations
description: Verifies every citation in a BibTeX .bib file against Crossref, DBLP, Semantic Scholar, and arXiv to catch hallucinated, fabricated, or incorrect references before reviewers do. Use when the user says verify citations, check references, validate bibliography, check my .bib, fake or hallucinated citations, retracted paper, or DOI check — and before any draft, rebuttal, or camera-ready leaves the machine. Flags unresolvable entries (likely fabrications), author/year/venue mismatches, duplicates, and retractions, and points to the canonical record for each fix. Every skill that writes or edits citations must route new references through this gate.
---

# Verify Citations

The anti-hallucination gate for bibliographies. Takes a `.bib` file, validates
every entry against live scholarly indexes (Crossref, DBLP, Semantic Scholar,
arXiv, DataCite), and produces a per-entry verdict: VERIFIED, MISMATCH,
UNRESOLVED (possible fabrication), or RETRACTED. One fabricated citation in a
submitted paper can end a review — or a reputation. Be rigorous here.

## When to use

- The user asks to verify, check, validate, or audit citations / references /
  a bibliography / a `.bib` file.
- Any writing skill (`draft-related-work`, `literature-review`,
  `write-rebuttal`, ...) added or edited citations — run this gate before
  declaring that work done.
- Before `preflight-check` / submission, camera-ready, or arXiv upload.
- The user suspects AI-generated references ("are these real papers?").

## Inputs

- A `.bib` file (path from the user, or find it: `*.bib` next to the main
  `.tex`, or the file named in `\bibliography{...}` / `\addbibresource{...}`).
- `CONTACT_EMAIL` environment variable — a real email, sent in the
  User-Agent so API providers can contact instead of block. Ask the user for
  it if unset; never invent one.
- Optional: `S2_API_KEY` for a dedicated Semantic Scholar rate allowance
  (the shared anonymous pool 429s under load; the script backs off and
  falls back to other providers automatically).

## Process

1. **Run the checker.** Deterministic work belongs to the script — do not
   verify entries by hand or from memory:

   ```bash
   export CONTACT_EMAIL=user@university.edu   # ask the user
   python3 scripts/check_bibtex.py path/to/refs.bib --json /tmp/citecheck.json
   ```

   Useful variants:
   - `--offline` — parse + duplicate/static checks only (no network; use when
     the user has no connectivity or only wants structural checks).
   - `--key smith2024` — re-check a single entry after a fix (repeatable).
   - `--no-retraction-check` — halves request count for very large files;
     keep retraction checks ON for any final pre-submission run.
   - `--strict` — exit nonzero on warnings too (CI gate mode).
   - `--refresh` — bypass the 24 h response cache in `.cache/`.

   Exit codes: `0` clean, `2` problems found, `1` operational failure (bad
   file, no network, missing CONTACT_EMAIL — fix the cause, do not skip the
   gate). For a 50-entry file expect ~2–4 minutes: the script is rate-limited
   to at most 1 request/second per host by design. Do not parallelize it and
   do not work around its politeness limits.

2. **Triage every flag.** Read [references/triage-guide.md](references/triage-guide.md)
   for what each flag means, known false positives (online-vs-print year
   off-by-one, venue aliasing, arXiv-vs-published versions, truncated author
   lists), and the exact fix for each. Severity at a glance:

   | Flag | Severity | Meaning |
   |---|---|---|
   | UNRESOLVED / DOI_NOT_FOUND / ARXIV_NOT_FOUND | ERROR | Not found in any index — possible fabrication |
   | TITLE_MISMATCH / AUTHOR_MISMATCH / YEAR_MISMATCH | ERROR | Identifier points at a different paper, or metadata is wrong |
   | RETRACTED | ERROR | A retraction notice exists for this DOI |
   | DUPLICATE_KEY / DUPLICATE_DOI / DUPLICATE_TITLE | ERROR | Same paper or key twice |
   | MALFORMED_DOI / MALFORMED_ARXIV_ID | ERROR | Identifier cannot be valid |
   | POSSIBLE_ID_TYPO / MISSING_DOI / VENUE_MISMATCH / AUTHOR_LIST_DIFFERS / TITLE_PARTIAL_MATCH / NOT_IN_INDEXES / EXPRESSION_OF_CONCERN | WARN | Real paper, imperfect entry — fix or justify |
   | UNVERIFIABLE_TYPE / RESOLVED_VIA_SEARCH / HAS_CORRECTION | INFO | Context for manual judgment |

3. **Fix only from canonical records.** Replace broken entries with BibTeX
   fetched from the authoritative source (DBLP `.bib` endpoint or doi.org
   content negotiation — exact commands in
   [references/triage-guide.md](references/triage-guide.md)). Never retype
   metadata from memory; that is how hallucinations get laundered into
   "fixes". Provider details, what each index is authoritative for, and the
   venue-alias problem are in
   [references/verification-sources.md](references/verification-sources.md).

4. **Escalate what cannot be fixed.** For each UNRESOLVED entry, present the
   evidence to the user and ask: keep (with a manual source they vouch for),
   fix (they supply the real reference), or remove (also remove the `\cite`
   and adjust surrounding text). Never decide silently, never delete
   silently, and never substitute a different paper that merely sounds
   similar.

5. **Re-run until exit code 0** (or until remaining flags are explicitly
   accepted by the user). Re-check just the fixed entries with `--key`, then
   do one full final pass.

6. **Report.** Summarize: N verified, list of fixes applied (old → new), list
   of user decisions taken, any flags the user accepted as-is. If this run
   gates another skill's output, state clearly whether the gate PASSED or
   FAILED.

## Output

- The script's per-entry report on stdout and, with `--json`, a
  machine-readable report (statuses, flags, resolved DOIs/URLs) the calling
  skill can act on.
- A corrected `.bib` (edits applied from canonical records, with the user's
  approval) and a short human summary of what changed and what remains open.

## Hard rules

- **Never fabricate a citation, DOI, arXiv ID, or BibTeX field.** If a
  reference cannot be verified, say so — an honest gap beats a confident
  fake.
- **Never "fix" an unresolved entry by guessing** which real paper was meant.
  Search, show candidates, let the user choose.
- A RETRACTED result must be surfaced to the user verbatim, with the
  retraction-notice DOI. Citing retracted work knowingly is sometimes
  legitimate (e.g., studying retractions) — that is the user's call, and the
  citation should then mark the retraction explicitly.
- Metadata only: this skill fetches and compares titles, authors, years,
  venues, DOIs. Do not store fetched abstracts or paper text in the repo.
- Retraction coverage is best-effort (Crossref/Retraction Watch data plus
  title markers); absence of a flag is not proof a paper stands. Say so when
  it matters.
- When using `venues/` profiles to judge a VENUE_MISMATCH, treat the profile
  as a starting point — re-verify any venue fact you rely on against the live
  `cfp_url` in the profile before telling the user their entry is wrong.

## Bundled resources

- `scripts/check_bibtex.py` — the verifier. Run it; do not reimplement it.
- [references/triage-guide.md](references/triage-guide.md) — flag-by-flag
  interpretation, false positives, exact remediation commands.
- [references/verification-sources.md](references/verification-sources.md) —
  provider APIs, authority order, venue aliasing, retraction data, rate
  limits and licensing.

## Memory

This skill uses the shared `.paper-memory/` convention in the user's paper
directory (full spec: [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `.paper-memory/lessons.md` to skip re-flagging entries the
  user already resolved this cycle, and lead with any `recurring` citation
  habits recorded for this author (e.g. "tends to cite arXiv preprints that are
  now published; prefer the published record").
- **At end:** append durable findings in the shared format `- [YYYY-MM-DD]
  (verify-citations | <scope>) issue -> recommendation` (via
  `reflect-and-improve`'s `reflect_log.py append`, which dedupes and dates). A
  pattern across the bibliography or across papers is `recurring`; a single
  fixed entry is `this-paper`. Never record fabricated metadata in memory, only
  the pattern and the canonical fix.
- Create `.paper-memory/` on demand if absent and offer to add it to the
  project `.gitignore`. It is local-only; never upload it or copy it into this
  repo.
