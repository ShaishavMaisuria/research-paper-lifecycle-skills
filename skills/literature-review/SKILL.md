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
2. Run the `verify-citations` skill on `references.bib`. Fix or drop anything
   unresolvable; flag retractions to the user.
3. Only after a key passes: `corpus.py set KEY --verified yes`.
   Never set `--verified yes` without that check — this is the
   anti-fabrication gate.

### Phase 7 — Draft

1. Write `review.md` following the structure templates in
   [references/review-structure.md](references/review-structure.md).
2. Every factual claim about prior work cites a corpus key: `[@key]` or
   `\cite{key}`. Claims must trace back to a note anchor — if there is no
   note, do not write the claim.

### Phase 8 — Gate

1. Run `python3 scripts/check_review.py <ws>/review.md`. It fails on unknown
   keys, unverified or excluded citations, placeholder markers, and verbatim
   quotes over 40 words; it warns on uncited included papers and uncited long
   paragraphs.
2. Fix and re-run until `RESULT: PASS`. Deliver only a passing document, and
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
  venue enumeration patterns, snowballing, stopping criteria, screening
  protocol.
- [references/claim-extraction.md](references/claim-extraction.md) — grounded
  note format, anchor and strength labels, copyright rules for notes.
- [references/review-structure.md](references/review-structure.md) — review
  document templates, synthesis matrix, citation syntax, handoffs to
  `draft-related-work` and `write-abstract`.
