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

**Resolving is necessary but not sufficient.** An identifier that resolves only
proves the entry points at *a* real record — not that it is the *right
instance* of the named work, nor that an independently-added reference is even
on-topic. The gate therefore goes beyond resolution with two non-fabricating
heuristics: a **canonical-instance** check (when a title exists as both, say, a
conference paper and a later RFC/tech-report/preprint, surface the
alternatives with citation counts so you cite the artifact the field cites)
and an opt-in **relevance gate** (score an added reference's topical fit and
flag low-fit ones for human review). And when an authoritative index is
unreachable, the run reports **PARTIAL-PASS**, never a clean PASS, naming the
checks that did not run — so "could not check" is never mistaken for "checked
and clean".

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
   - `--strict` — exit nonzero on warnings *and* on PARTIAL-PASS (CI gate
     mode: a gate run that could not reach an index has not run).
   - `--refresh` — bypass the 24 h response cache in `.cache/`.
   - `--thesis-file thesis.txt --core-key dean2008 --core-key vaswani2017` —
     turn on the **relevance gate** for independently-gathered additions:
     pass a plain-text thesis/abstract and the keys you have already confirmed
     are core; low-topical-fit entries get a `LOW_RELEVANCE` flag for review.
     Use this when another skill (`draft-related-work`, `literature-review`)
     added references and you need to tell good additions from off-topic ones.
   - `--no-canonical-instance` — skip the extra same-title lookup that powers
     the `CANONICAL_INSTANCE` wrong-artifact check (on by default).
   - `--no-soft-fail` — abort (exit 1) the instant any index is unreachable,
     instead of degrading to PARTIAL-PASS.

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
   | CANONICAL_INSTANCE | WARN | Resolves, but a *different artifact* of the same work is what the field cites — pick the canonical instance |
   | LOW_RELEVANCE | WARN | Resolves, but scored low topical fit to the paper — confirm it is load-bearing, never auto-remove |
   | UNVERIFIABLE_TYPE / RESOLVED_VIA_SEARCH / HAS_CORRECTION / RELEVANCE_OK / CHECK_SKIPPED | INFO | Context for manual judgment |

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

   For `CANONICAL_INSTANCE` and `LOW_RELEVANCE` (both WARN), see
   [references/triage-guide.md](references/triage-guide.md) and
   [references/relevance-gate.md](references/relevance-gate.md). These are
   copilot prompts, not autopilot actions: surface the alternative artifact /
   the low-fit score and let the user decide. The script's lexical relevance
   score is a deterministic proxy — if you have an embedding model available,
   compute abstract-embedding similarity yourself for a stronger signal before
   advising, as the relevance-gate reference explains. Never auto-swap an
   instance or auto-delete a low-fit reference.

5. **Re-run until exit code 0** (or until remaining flags are explicitly
   accepted by the user). Re-check just the fixed entries with `--key`, then
   do one full final pass. If a run came back PARTIAL-PASS because an index
   was unreachable, that is not done — re-run the skipped checks once
   connectivity returns before declaring the gate clean.

6. **Report.** Summarize: N verified, list of fixes applied (old → new), list
   of user decisions taken, any flags the user accepted as-is, and any
   wrong-artifact / low-relevance items raised for the user's judgment. State
   the script's overall verdict explicitly — **PASS**, **PARTIAL-PASS** (and
   which checks did not run), or **FAIL**. If this run gates another skill's
   output, report the verdict verbatim; never upgrade a PARTIAL-PASS to
   "passed", and never promise acceptance or a clean review.

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
- **Resolution is not endorsement.** A resolving DOI/ID proves the record is
  real, not that it is the right *instance* or topically relevant. Treat
  `CANONICAL_INSTANCE` and `LOW_RELEVANCE` as copilot prompts: surface the
  evidence, never auto-swap the artifact or auto-remove the reference.
- **Never invent a citation count, an alternative artifact, or a relevance
  score.** Every alternative the canonical-instance check shows must be a
  record an index actually returned; every relevance number comes from the
  script or from an embedding model you actually ran — not from memory.
- **A PARTIAL-PASS is not a PASS.** If any authoritative index was
  unreachable, report PARTIAL-PASS, list the skipped checks, and re-run them
  before treating the bibliography as verified. Never let "could not check"
  read as "clean".
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
  interpretation, false positives, exact remediation commands (includes
  `CANONICAL_INSTANCE` and the PARTIAL-PASS verdict).
- [references/relevance-gate.md](references/relevance-gate.md) — how the
  relevance gate scores topical fit, the embedding-similarity upgrade you
  should run when a model is available, and how to act on `LOW_RELEVANCE`.
- [references/verification-sources.md](references/verification-sources.md) —
  provider APIs, authority order, venue aliasing, retraction data, rate
  limits and licensing.

## Memory

This skill uses the shared `.paper-memory/` convention in the user's paper
directory (full spec:
[`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

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
