# Grounded claim extraction

How to read one paper and produce notes that can back citations in the final
review. The rule that makes the whole skill trustworthy: **a claim may appear
in the review only if a note anchors it to a specific place in a real paper.**

## The note file

One file per included paper: `notes/<key>.md`, where `<key>` is the corpus
cite key. Template:

```markdown
# <key> — <title> (<venue> <year>)

Source read: <arXiv HTML | OA PDF via Unpaywall | dl.acm.org PDF> on <date>
Relevance: one line on why this paper is in the review.

## Claims

- CLAIM: Their learned index cuts range-query latency 2.1x vs an R-tree
  on uniform data.
  ANCHOR: §5.2, Table 3
  STRENGTH: shown
- CLAIM: The approach assumes static data; updates are left to future work.
  ANCHOR: §7, last paragraph
  STRENGTH: stated
- CLAIM: Positions itself as the first learned structure for spatial joins.
  ANCHOR: §1, contributions list
  STRENGTH: claimed

## Method (2-4 lines, your words)

## Evaluation setup (datasets, baselines, metrics — your words)

## Limitations the paper admits / you observe

## Theme candidates: <slug>, <slug>
```

## Claim records

Each claim has three parts:

- **CLAIM** — one sentence, your paraphrase, specific enough to cite later.
  Numbers are the most valuable claims; copy numbers exactly, with their
  conditions ("2.1x *on uniform data*").
- **ANCHOR** — where in the paper: section number, table/figure number, or
  page. The anchor is what lets anyone (including `verify-citations`-grade
  scrutiny later) re-check the claim. A claim without an anchor does not
  exist.
- **STRENGTH** — how the paper supports it:
  - `shown` — backed by an experiment/proof in the paper
  - `stated` — asserted by the authors without direct evidence in-paper
  - `claimed` — positioning/novelty claims about other work
  - `secondary` — the paper citing someone else (prefer going to the
    original; if you cite the original, fetch and verify the original)

In the review, match language to strength: "X demonstrates…" only for
`shown`; "X argues/reports…" for `stated`; never upgrade a `claimed` into a
fact.

## Copyright and transience rules (hard rules)

- Notes are **your words**. Never paste paragraphs, abstracts, or contiguous
  sentences from the paper.
- Verbatim quotes: only when the exact wording matters, **under 25 words**,
  inside quotation marks, with an anchor. (`check_review.py` hard-fails
  quotes over 40 words in the final document, including quotes that wrap
  across lines. The guard only sees quotation-marked spans — transcribed
  text *without* quote marks is invisible to it, which is exactly why the
  paraphrase discipline in this file is a rule, not a suggestion.)
- Fetched PDFs/HTML are transient: read them where `resolve_oa.py` put them
  (temp dir), do not copy them into the workspace or repo, do not commit
  them.
- Figures/tables: describe them; never extract or reproduce them.

## Reading order for speed

1. Abstract + intro contributions list → relevance and `claimed` records.
2. Evaluation section tables → the `shown` numbers (the highest-value claims).
3. Conclusion/limitations → `stated` records and gap material.
4. Method section only as deep as the review's themes require.

Budget ~10 minutes of reading per paper for a standard review; go deeper only
for the 2–3 papers central to the user's own work.

## After each paper

1. Save the note file.
2. `python3 scripts/corpus.py --corpus ... set KEY --extracted yes`.
3. Add theme candidates to the bottom of the note — themes are clustered
   across papers in Phase 5, not invented one paper at a time.
