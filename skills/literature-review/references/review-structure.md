# Review document structure

Templates and conventions for the final `review.md`.

## Contents

- [Citation syntax](#citation-syntax)
- [Choosing themes](#choosing-themes)
- [The standard template](#the-standard-template)
- [The synthesis matrix](#the-synthesis-matrix)
- [Writing the theme sections](#writing-the-theme-sections)
- [Gaps section](#gaps-section)
- [Handoffs to other skills](#handoffs-to-other-skills)

## Citation syntax

Use pandoc-style keys throughout: `[@li2024learned]`, multiple
`[@a; @b; @c]`. LaTeX `\cite{...}`/`\citep`/`\citet` is also recognized by
the gate. Keys must match `corpus.json` exactly. The document converts
cleanly: pandoc renders it with `references.bib`; for LaTeX hand-off, replace
`[@x]` with `\cite{x}` mechanically.

Rules the gate (`scripts/check_review.py`) enforces:

- every cited key exists in the corpus → unknown key = FAIL
- every cited key is `verified` (Phase 6) → unverified = FAIL
- no citation of `excluded` papers → FAIL
- no `[CITATION NEEDED]` / `[@TODO]` / `??` placeholders → FAIL
- no verbatim quote over 40 words (even wrapped across lines) → FAIL —
  the guard only detects quotation-marked spans, so unmarked transcription
  is a copyright violation the gate cannot catch; paraphrase regardless
- included+extracted papers should all be cited → WARN (`--strict` to FAIL)

## Choosing themes

3–6 themes, clustered from the theme candidates at the bottom of the note
files. Good themes are *axes of the problem* (e.g. "index structures",
"query optimization", "learned cost models"), not paper types ("surveys",
"recent work") and not one-paper buckets. Tests:

- every theme has ≥2 papers (a 1-paper theme is a paragraph, not a theme);
- a reader could predict which theme a new paper belongs to;
- themes together answer the research question.

Record in `themes.yml` (slug, one-line definition, paper keys) and tag the
corpus (`corpus.py set KEY --theme slug`) so coverage is auditable.

## The standard template

```markdown
# Literature review: <topic>

## 1. Scope and method
Research question; inclusion/exclusion criteria; providers + query variants
+ search date; counts found → screened → included; stopping criterion.

## 2. Themes
### 2.1 <Theme A>          # one subsection per theme
### 2.2 <Theme B>

## 3. Synthesis matrix     # the table, see below

## 4. Gaps and open problems

## 5. References           # rendered from references.bib (verified)
```

For a short review (≤8 papers), the matrix may replace per-theme subsections;
keep Scope and Gaps regardless.

## The synthesis matrix

One row per included paper:

| Paper | Theme | Approach | Evaluation | Key result |
|---|---|---|---|---|
| [@li2024learned] | learned-structures | RMI over Hilbert keys | 3 real datasets vs R-tree | 2.1x range-query speedup (uniform) [@li2024learned] |

Every cell with a factual claim carries the row's key. Pull "Key result"
straight from `shown` claim records — numbers with their conditions.

## Writing the theme sections

Per theme, 2–4 paragraphs in this movement:

1. **Frame** the sub-problem in one or two sentences (your synthesis — this
   is where an uncited topic sentence is acceptable; keep it short or the
   bare-paragraph warning fires).
2. **Compare**, don't enumerate. "X and Y both do A [@x; @y], but only Y
   handles B [@y]" beats two disconnected summaries. Group papers by
   approach within the theme.
3. **Verb discipline** (from claim strengths): `shown` → "demonstrates,
   reduces, outperforms"; `stated` → "reports, argues"; `claimed` → "claims,
   positions itself as". Never promote a claim above its strength label.
4. **Close** with what the theme leaves unsolved — these sentences seed the
   Gaps section.

Each factual sentence about a paper must trace to a claim record in
`notes/<key>.md`. No note, no sentence.

## Gaps section

Gaps must be *evidenced absences*, not wishes: "none of the learned
structures handle updates [@li2024learned; @kim2025lsm]" (citing the papers
whose limitations sections admit it) — not "more research is needed". 3–5
gaps, each one paragraph, each cited. If the review feeds the user's own
paper, mark which gap their work addresses.

## Handoffs to other skills

- **`draft-related-work`** — for a Related Work section inside a paper:
  hand over `corpus.json`, `notes/`, and `references.bib`; that skill owns
  positioning against the user's contribution and venue conventions.
- **`verify-citations`** — re-run whenever references.bib changes; the gate
  requires per-key `verified` status.
- **`write-abstract`** — a standalone survey being submitted somewhere needs
  venue-aware abstract norms.
- **`find-papers` / `fetch-paper`** — any late addition goes through the
  full pipeline (search hit → screen → fetch → extract → verify), never
  straight into the references.
