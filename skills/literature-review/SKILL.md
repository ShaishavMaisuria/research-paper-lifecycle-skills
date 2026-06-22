---
name: literature-review
description: Builds a structured literature review — survey of prior work, state of the art, related-work landscape — where every claim cites a verified reference. Use when the user says "literature review", "lit review", "survey the papers on X", "what's the state of the art", "synthesize prior work", or "organize these papers by theme". Composes sibling skills, search via find-papers (key-free DBLP/Crossref/Semantic Scholar/arXiv), full text via fetch-paper (legal open-access only), and citation checking via verify-citations. Tracks a screening corpus, extracts claims with section-level anchors, organizes by theme, and gates the final document with a deterministic checker so no claim ships uncited, unverified, or resting on a fabricated reference.
---

# Literature Review

Produce a themed, citation-grounded review document from a research question.
This skill is the orchestrator: searching, fetching, and citation verification
are delegated to sibling skills; this skill owns the workspace, the screening
corpus, claim extraction, thematic synthesis, and the final coverage gate.

## When to use

- "Do a literature review on X" / "survey recent work on X"
- "What's the state of the art in X since 2023?"
- "Read these N papers and synthesize them by theme"
- A standalone survey is wanted. For a paper's Related Work *section*,
  do the corpus-building phases here, then hand off to `draft-related-work`.

## Inputs

- A research question or topic, ideally with year range and (optionally)
  target venues.
- `CONTACT_EMAIL` exported for the sibling skills' API politeness contract.
- Optional: an existing list of papers/DOIs the user already has.

## Sibling skills this skill delegates to

| Stage | Delegate to | What it provides |
|---|---|---|
| Search | `find-papers` | `dblp_search.py`, `crossref_search.py`, `s2_search.py`, `arxiv_search.py` (in that skill's script dir) — key-free, rate-limited, cached |
| Full text | `fetch-paper` | `resolve_oa.py` — one DOI/arXiv ID → legal OA copy, transient |
| Reference check | `verify-citations` | validates every BibTeX entry against Crossref/DBLP/S2, flags retractions |

Never reimplement these inline (no ad-hoc `curl` against scholarly APIs);
the sibling scripts carry the rate-limit, backoff, caching, and User-Agent
contract.

## Process

### Phase 1 — Scope

1. Pin down with the user: research question, year range, inclusion and
   exclusion criteria (2–4 each), target size (10–15 papers is a solid
   default; >30 needs explicit user buy-in).
2. Run `python3 scripts/init_review.py "TOPIC"` — creates
   `lit-review/<slug>/` with `corpus.json`, `themes.yml`, `notes/`, and a
   `review.md` skeleton.
3. Write the agreed criteria into `corpus.json` under `criteria`.

### Phase 2 — Search (delegate to find-papers)

1. Follow [references/methodology.md](references/methodology.md) for query
   design, venue enumeration, and snowballing.
2. If the scope names venues, read `venues/conferences/<id>.yml` for the
   `aliases` block (DBLP key, S2 venue string, Crossref container title) —
   this solves the venue-alias problem. Profiles are a starting point: if any
   profile fact becomes load-bearing for the review (e.g. which tracks exist),
   re-verify it against the live `cfp_url` before relying on it.
3. Record every search hit batch:
   `python3 scripts/corpus.py --corpus <ws>/corpus.json import hits.json
   --source dblp --query "..."` (accepts `find-papers --json` output;
   dedupes on DOI). Add single papers with `corpus.py add`.
4. Snowball from **multiple, topically-diverse seeds — one per theme**, not a
   single convenient paper (which drifts the harvested set into one sub-area
   and misses the rest). Admit each neighbor only if you can name its role in
   the question's argument (method-we-extend / baseline / eval-task /
   foundational-lineage), and run the co-citation sanity check before
   screening. Full protocol in
   [references/methodology.md](references/methodology.md#snowballing).
5. **Treat a degraded search as not-yet-done, not done.** `find-papers`'
   `resolve_papers.py` stamps each fan-out COMPLETE or PARTIAL and flags any
   result confirmed by only a single index. If a theme's search comes back
   PARTIAL (a provider was rate-limited), or its core papers are single-index
   only, the citation-graph stage silently fell back — recall for that theme
   rests on luck. Re-issue the rate-limited leg after a cool-down (add
   `S2_API_KEY`) or substitute a provider before declaring the theme covered;
   record in `corpus.json` which papers were recoverable only via a fallback
   path so the gap is auditable.

### Phase 3 — Screen

1. For each pending paper, decide included/excluded against the written
   criteria using title + venue + (fetched-on-demand) abstract. Use
   `s2_search.py` from find-papers for abstracts — never paste abstracts
   into any committed file.
2. Record every decision with a reason:
   `python3 scripts/corpus.py --corpus ... set KEY --screened excluded
   --reason "out of scope: no spatial component"`.
3. Show the user `corpus.py stats` and the included list before reading
   full texts. Confirm the set.

### Phase 4 — Fetch and extract (delegate to fetch-paper)

1. One paper at a time, run fetch-paper's resolver (from the repo root):
   `FP=skills/fetch-paper/scripts; python3 "$FP/resolve_oa.py" <DOI-or-arXiv-ID>`.
   Read the OA copy transiently — prefer arXiv HTML, else
   the PDF directly. If no legal OA copy exists (exit code 3), mark the paper
   and synthesize from verified metadata only, or ask the user for their
   library copy. Never use shadow libraries.
2. Take grounded notes into `notes/<key>.md` using the claim-record format in
   [references/claim-extraction.md](references/claim-extraction.md): each
   claim gets an anchor (section/page), a strength label, and paraphrase only
   (verbatim quotes < 25 words, always quoted). Never store abstracts or
   paper text — notes are your words.
3. Mark progress: `corpus.py set KEY --fetched yes --extracted yes`.

### Phase 5 — Organize by theme

1. Cluster the extracted claims into 3–6 themes; record them in `themes.yml`
   and tag papers: `corpus.py set KEY --theme <slug>`.
2. Build the synthesis matrix (paper × theme × approach × evaluation × result)
   per [references/review-structure.md](references/review-structure.md).

### Phase 6 — Verify citations (delegate to verify-citations)

1. Generate skeleton BibTeX:
   `python3 scripts/corpus.py --corpus ... bibtex > <ws>/references.bib`.
   `corpus.py` is the **single source of truth for cite keys** — `bibtex`
   emits the `.bib` with the corpus's exact keys. Never hand-edit a key in the
   `.bib`; change it in the corpus (`corpus.py add --update`) and regenerate,
   so the corpus, the `.bib`, and the review's `[@key]`s never diverge.
2. Run the `verify-citations` skill on `references.bib`, **always with
   `--json`** so there is a machine artifact to reconcile against:
   `check_bibtex.py <ws>/references.bib --json <ws>/citecheck.json`. Fix or
   drop anything unresolvable; flag retractions to the user.
3. Set verified flags **from that artifact, not by hand**:
   `python3 scripts/corpus.py --corpus <ws>/corpus.json verify-audit
   --report <ws>/citecheck.json`. The audit marks `verified:yes` *only* for
   keys the report confirmed (status VERIFIED), clears any flag the report did
   not confirm, records `verified_via` provenance + the date, and echoes the
   report's verdict line verbatim. It **exits nonzero on a PARTIAL-PASS or
   FAIL** — so an incomplete run cannot read as clean.
   - If you set a flag manually instead, `corpus.py set KEY --verified yes`
     now **requires `--source <provider>`** (the index whose canonical record
     confirmed the entry) and records it; a bare `--verified yes` is rejected.
   - "Verified" means an authoritative index actually returned the canonical
     record for this entry *this session* — not merely that some API echoed an
     id once, and never with `fetched:false`. A key marked `verified:yes` with
     no provenance is a broken gate; `corpus.py stats` now WARNs when it sees
     one.
   - Mirror the verify-citations verdict line **verbatim** in the review's
     prose and any summary/README: the exact verdict (PASS / PARTIAL-PASS /
     FAIL) plus raw counts (N verified, M warnings by flag, K skipped checks).
     Never upgrade a PARTIAL-PASS to "verified", and never collapse
     "PARTIAL-PASS, 11 WARN, 1 skipped" into "verified, 0 errors".

### Phase 7 — Draft

1. Write `review.md` following the structure templates in
   [references/review-structure.md](references/review-structure.md).
2. Every factual claim about prior work cites a corpus key: `[@key]` or
   `\cite{key}`. Claims must trace back to a note anchor — if there is no
   note, do not write the claim.

### Phase 7b — Reconcile forward references

The draft (and any related-work plan) names methods, baselines, and backbones
in prose as slots — "we extend X", "compared against Y", "built on the W
backbone". Make sure none ship unbacked:

1. Run `python3 scripts/forward_refs.py <ws>/review.md [plan.md]
   --corpus <ws>/corpus.json`. It extracts every named method/baseline/
   backbone, diffs against the verified corpus, and emits the unresolved ones
   as a **retrieval worklist**.
2. For each genuine missing work, loop it back through the full pipeline
   (find-papers → screen → fetch-paper → extract → verify-citations) before
   the corpus is declared complete. Dismiss only the entries that are not
   citable works (the user's own system, a dataset, a metric) — never invent a
   citation to clear the list.
3. Re-run until the worklist holds no real references.

### Phase 8 — Gate

1. Assert the corpus and `references.bib` keys are in lock step:
   `python3 scripts/corpus.py --corpus <ws>/corpus.json check-keys
   <ws>/references.bib`. If it fails, regenerate the `.bib` from the corpus
   (`corpus.py bibtex`) — never reconcile by hand-editing keys.
2. Run `python3 scripts/check_review.py <ws>/review.md --bib
   <ws>/references.bib`. It fails on unknown keys, unverified or excluded
   citations, any cited key missing from the `.bib` (key drift), placeholder
   markers, and verbatim quotes over 40 words; it warns on uncited included
   papers and uncited long paragraphs.
3. Fix and re-run until `RESULT: PASS`. Deliver only a passing document, and
   tell the user the review passed the coverage gate.

## Output

- `lit-review/<slug>/review.md` — the themed review, every claim cited,
  gated by `check_review.py`.
- `lit-review/<slug>/corpus.json` — auditable trail: searches, screening
  decisions with reasons, verification status.
- `lit-review/<slug>/references.bib` — verified BibTeX.
- `lit-review/<slug>/notes/` — per-paper grounded notes (paraphrase only).

## Guardrails

- Never fabricate or embellish a citation. A paper enters the review only via
  a real search hit, and a citation ships only after `verify-citations`
  passes it. If evidence for a claim is missing, say so instead.
- Copyright: paper text and abstracts are fetched on demand and processed
  transiently — never written into the workspace, the repo, or the review.
  Metadata (DOI, title, authors, BibTeX fields) is fine. Quotes < 25 words,
  marked and cited.
- Politeness: all network access goes through the sibling skills' scripts
  (≤1 req/s per host, `CONTACT_EMAIL` User-Agent, 429 backoff, `.cache/`).
- Never submit or post anything on the user's behalf.
- Present screening decisions and the final theme structure to the user for
  approval — the user owns scope judgments.

## References

- [references/methodology.md](references/methodology.md) — query design,
  venue enumeration patterns, multi-seed snowballing with role-based inclusion
  and a co-citation sanity check, stopping criteria, screening protocol,
  forward-reference reconciliation.
- [references/claim-extraction.md](references/claim-extraction.md) — grounded
  note format, anchor and strength labels, copyright rules for notes.
- [references/review-structure.md](references/review-structure.md) — review
  document templates, synthesis matrix, citation syntax, handoffs to
  `draft-related-work` and `write-abstract`.
