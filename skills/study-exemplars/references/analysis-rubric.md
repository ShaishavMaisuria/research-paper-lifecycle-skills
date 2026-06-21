# Exemplar Analysis Rubric

The dimensions for an original style-and-structure analysis of venue
exemplars. Work through every dimension for every paper, recording facts
and observations; then synthesize across papers. The synthesis — not the
per-paper notes — is what the user writes against.

## Table of contents

1. [The copyright line for everything you write down](#1-the-copyright-line)
2. [Identity card (metadata)](#2-identity-card)
3. [Title and abstract patterns](#3-title-and-abstract-patterns)
4. [Section architecture](#4-section-architecture)
5. [Introduction and contribution framing](#5-introduction-and-contribution-framing)
6. [Method presentation](#6-method-presentation)
7. [Evaluation patterns](#7-evaluation-patterns)
8. [Figure and table conventions](#8-figure-and-table-conventions)
9. [Related-work positioning](#9-related-work-positioning)
10. [Reproducibility, limitations, and compliance apparatus](#10-reproducibility-limitations-and-compliance-apparatus)
11. [Writing micro-style](#11-writing-micro-style)
12. [Cross-paper synthesis template](#12-cross-paper-synthesis-template)
13. [Exemplar card template](#13-exemplar-card-template)
14. [Cache a measured exemplar bundle](#14-cache-a-measured-exemplar-bundle)

## 1. The copyright line

Everything recorded under this rubric must be **original analysis** —
facts and observations about the paper, in your own words. Facts about
structure, counts, ordering, and conventions are not copyrightable
expression; the paper's prose, abstract, figures, and tables are.

**Allowed in notes and in the brief:**

- Metadata: title, authors, year, venue, DOI, pages, award, citation count
- Structural facts: section names and order, counts (figures, tables,
  baselines, datasets, references), page allocation per section
- Observations and characterizations in your own words ("the intro closes
  with a four-bullet contribution list, each bullet naming a section")
- At most ONE short attributed quote per paper, under 25 words, used only
  when the exact wording IS the observation (e.g. a contribution-bullet idiom)

**Never in notes, the brief, or any committed file:**

- The abstract, or any paragraph/passage reproduced verbatim or
  lightly paraphrased
- Extracted figures, tables of results, or pseudocode lifted from the paper
- The PDF or its converted text, in whole or part

## 2. Identity card

Record for every exemplar:

- Title, authors (first 3 + et al.), year, venue + track, DOI / arXiv ID
- Why it is in the set: `award (<award name>, <source URL>)` or
  `top-cited (rank N in <year window>, M citations per S2 on <date>)`
- Page count, and the page limit in force that year if discoverable
  (older exemplars may have written to a different limit — flag in §12)
- OA copy used: URL + version (`publishedVersion` / `acceptedVersion` /
  `submittedVersion`); preprint analysis must note the camera-ready may differ

## 3. Title and abstract patterns

- Title form: system-name colon pattern ("Foo: Bar for Baz")? Question?
  Claim? Length in words; presence of the method name, the task, a number
- Abstract: sentence count and the move sequence — context → problem/gap →
  approach → key result(s) → impact. Which moves get how many sentences?
  Does it quantify results ("up to 3.4× faster")? Does it name datasets,
  systems, or theorems?
- Do abstracts state the contribution type explicitly (system, benchmark,
  theory, measurement)?

## 4. Section architecture

- The skeleton: exact top-level section names in order (e.g. Intro |
  Related Work | Preliminaries | Method | Experiments | Conclusion)
- Related-work placement: §2 vs. before the conclusion vs. woven into
  the intro — this is a strong community signal, record it for every paper
- Page allocation: roughly how many pages/columns each top-level section
  takes; what fraction of the paper is evaluation (data/ML venues often
  spend 30–40% on experiments; theory venues invert this)
- Depth: are there sub-sub-sections? Numbered definitions/theorems?
- Special sections: Preliminaries/Background present? Problem Statement as
  its own section? A separate Discussion? Case study? Appendix usage and
  what gets pushed there (proofs, extra experiments, prompts)

## 5. Introduction and contribution framing

The single highest-value dimension — record in detail:

- Intro length (columns/paragraphs) and the paragraph-by-paragraph move
  structure: hook (application? statistic? trend?) → why now → gap in
  prior work → why the gap is hard → this paper's approach → contributions
- The gap move: how is prior work shown insufficient — dimension table?
  "however" pivot? explicit failure example with numbers?
- Contribution statement: bulleted list or prose? How many bullets? Are
  bullets typed (technique / theory / system / evaluation)? Do they
  cross-reference sections? Do they quantify?
- Is there a teaser figure on page 1 (Figure 1 as the whole-idea picture)?
  What kind — architecture, example, headline-result chart?
- Claim calibration: "we propose the first…" vs. hedged claims; how do
  award papers scope their novelty sentences?

## 6. Method presentation

- Formalization level: prose-first, definition–theorem–proof, or
  algorithm-box-driven? Notation table present?
- Running example: is one concrete example threaded through the method?
- Architecture/overview figure: present? Referenced subsection-by-subsection?
- Pseudocode: how many algorithm boxes, what granularity, line-numbered?
- Complexity analysis: stated where (end of method vs. appendix)?
- How are design choices justified — ablation forward-references,
  "we choose X because", or theory?

## 7. Evaluation patterns

- Experimental questions: are experiments organized around explicit RQs
  ("RQ1: …")? How many?
- Datasets: how many, which ones, real vs. synthetic, sizes stated? Is
  there a dataset summary table?
- Baselines: how many, are they recent (within 2–3 years), grouped by
  family? Self-ablations counted separately?
- Metrics: which, how many; statistical rigor — repeated runs, variance
  /error bars, significance tests, confidence intervals?
- Standard experiment suite for this venue: effectiveness + efficiency +
  scalability + ablation + parameter sensitivity + case study — which
  subset is universal in the exemplar set?
- Hardware/setup disclosure: where, how detailed?
- Negative results / failure analysis: present at all?

## 8. Figure and table conventions

- Counts: figures and tables per paper (and per page of evaluation)
- The page-1 teaser convention (see §5) — universal, common, or absent?
- Figure style: multi-panel (a)(b)(c) grids? Line plots vs. bars; log
  axes; colorblind-safe palettes; legend placement; font size relative
  to body text
- Table style: booktabs rules (no vertical lines)? Best results bolded,
  second-best underlined? Up/down arrows for metric direction? Std-dev
  in parentheses?
- Captions: one-liner vs. self-contained mini-paragraphs that interpret
  the result; caption position (above tables, below figures)
- Where do figures sit — column-width vs. page-width, top-of-page floats?

## 9. Related-work positioning

- Organization: thematic subsections vs. one chronological wall; how many
  themes; theme names
- The positioning move: does each theme paragraph end by contrasting the
  paper ("unlike these, we…")? Is there a comparison table of prior work
  vs. dimensions?
- Citation density: rough reference count; share of references from the
  last 3 years; share from this same venue (community signal)
- Tone toward prior work: deferential, neutral, or sharp?

## 10. Reproducibility, limitations, and compliance apparatus

- Code/data link: present? Where (abstract footnote, intro, dedicated
  section)? Anonymous repo at submission?
- Artifact badges (ACM), reproducibility checklists (NeurIPS checklist,
  ICML impact statement), ethics statements — which appear, where?
- Limitations: dedicated section, woven into discussion, or absent?
- Acknowledgments/funding conventions (camera-ready only at double-blind
  venues — note which version you analyzed)

## 11. Writing micro-style

- Voice: "we" vs. passive; present vs. past tense in method and results
- Paragraph discipline: topic-sentence-first? Typical paragraph length?
- Signposting: "The rest of this paper is organized as follows" present
  or dropped (increasingly dropped at page-tight venues)?
- Sentence rhythm in award papers vs. ordinary ones: shorter sentences,
  more concrete nouns, fewer hedges?
- Terminology discipline: one name per concept throughout?

## 12. Cross-paper synthesis template

Aggregate after all papers are analyzed. For each dimension above, state
the venue convention with evidence tags:

```markdown
## Venue conventions — <venue> (from N exemplars, years Y1–Y2)

### Section architecture
- Convention: <observed in k/N papers> …
- Variant: <papers A, B do X instead> …

### Contribution framing
- …

(continue per rubric dimension)

### Deltas vs. the current CFP
- <exemplar habit> conflicts with <live CFP rule, verified <date>> — follow the CFP.
```

Rules: a "convention" needs at least half the exemplar set; below that,
report a split, never average it away. Tag every claim with the papers
exhibiting it. Where awardees and top-cited papers diverge, say so —
awardees show what the committee rewards *now*; top-cited show what aged
well.

## 13. Exemplar card template

One per paper, kept compact (25 lines or fewer):

```markdown
### <Title> (<year>) — <selection reason>
- <authors, first 3 et al.> · DOI <doi> · <track> · <pages> pp · OA: <url> (<version>)
- Skeleton: <§ names in order; related-work position>
- Intro/contributions: <moves; bullet count; teaser figure y/n>
- Method: <formalization level; figures; pseudocode>
- Evaluation: <datasets/baselines/metrics counts; RQs; ablations; rigor>
- Figures/tables: <counts; styles; caption style>
- Notable: <1–3 original observations worth imitating — own words>
- Optional quote: "<25-word fragment>" (<section>, p. <n>)
```

## 14. Cache a measured exemplar bundle

The per-paper *facts* you just recorded (section skeletons, figure/table/
reference counts, abstract word counts, teaser/badge presence) are not
copyrightable expression — they are exactly the on-family distribution that
downstream skills (e.g. `benchmark-paper`) score a draft against. The
problem this step solves: when a downstream skill's **live exemplar fetch is
skipped or rate-limited**, it falls back to the venue/family profile's
`exemplar_distribution:` block — and for most venues that block is *hand-
estimated*, never measured against real papers. A study session is the one
moment those numbers can be measured, so cache them.

**While analyzing each paper, also record the bundle inputs** (a number per
field, never any text) into a small JSON file — one object per exemplar:

```json
{
  "venue": "<S2 venue string>", "recency": "<Y1-Y2>",
  "basis": "best-paper awardees + top-cited",
  "source_urls": ["<award list>", "<proceedings index>"],
  "papers": [
    {"id": "doi:10.1145/…", "pages": 12, "refs": 58, "figures": 9,
     "tables": 4, "abstract_words": 187, "teaser_figure": true,
     "artifact_badge": true,
     "sections": ["Introduction","Related Work","Method","Experiments","Conclusion"]}
  ]
}
```

Only counts, lengths, booleans, and section *names* — **never** abstracts,
passages, figures, or pseudocode. Every paper needs a verified `id`.

Then aggregate into a provenance-stamped block:

```bash
python3 scripts/build_exemplar_bundle.py measurements.json --out block.yml
```

The script emits a schema-conforming `exemplar_distribution:` block: density
**bands** ([p10, p90], never a fabricated single point), rates, and the modal
section skeleton — each annotated with how many papers it was measured from.
It stamps `measured: true`, `n`, `recency`, `as_of: <date>`, and a
`confidence` of `measured` (≥3 papers, clean) or `measured-low-confidence`
(thin or flagged). It **invents nothing**: a band with <3 reporting papers is
emitted as `null` (left for a live fetch), identical-everywhere numbers are
flagged as a likely stub, and a paper without an `id` is rejected.

**Caching rule (data hygiene, every venue):**

- Paste the emitted block into the relevant profile under review — the
  conference profile `venues/conferences/<id>.yml` for venue-specific
  measurements, or the `venues/families/<family>.yml` profile when the set
  spans the family. **Replace any hand-estimated block** with the measured
  one; if you only have a thin set, keep `measured-low-confidence` so the
  consumer knows the basis is shallow rather than overclaiming.
- This upgrades the downstream fallback from "hand-written family
  description" to "real measured exemplars". It does **not** make the cache
  ground truth: a live `study-exemplars` corpus for the *target venue* still
  wins, and the cache is the labelled fallback when a live fetch fails.
- The block is metadata only (counts, bands, section names, URLs, a date) —
  safe to commit under the copyright contract in §1. Never cache paper text.

**Provenance labelling rule:** because the block carries `measured` and
`as_of`, every score a consumer derives from it can — and must — disclose its
basis as **cache-vs-live**: `live` (a corpus built this session), `family-
prior (measured, as_of <date>)`, `family-prior (hand-estimated)`, or `none`.
Never let a cache-derived score read as if it were measured live this session.
