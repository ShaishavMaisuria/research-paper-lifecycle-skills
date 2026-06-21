# Originality detection methods

Five complementary methods. No single one is sufficient — run several and combine, because each sees a different kind of overlap and each has blind spots. Be explicit with the user about what each can and cannot catch.

## 1. Source overlap (shingling)
- **How:** `overlap_check.py --draft X --against S1 S2 …` builds word k-grams (default k=8) of each source and finds matching runs in the draft, merged into passages, with an overlap %.
- **Catches:** verbatim and near-verbatim copying from a known source.
- **Blind to:** sources you didn't supply; heavy paraphrase (different words, same idea).
- **Threshold:** default flag at ≥15% of the draft overlapping one source; *any* multi-sentence exact passage is worth review even below that.

## 2. Self-plagiarism / text recycling
- **How:** run source overlap with the author's **own prior papers** as sources, plus `--self` for internal near-duplicate paragraphs (difflib ratio ≥0.80).
- **Catches:** reused method/related-work boilerplate, duplicate submission overlap, recycled paragraphs.
- **Why it matters:** most venues treat substantial reuse of your own published text as a violation even though it's "your" writing. Report it; advise disclosure, rewrite, or citation of the prior work.

## 3. Quote & paraphrase integrity
- **How:** for each flagged passage, classify: (a) legitimate quotation → must have quotation marks **and** a citation; (b) close paraphrase → too few words changed from the source, rewrite genuinely; (c) copied → remove or quote+cite.
- **Catches:** the most common honest mistake — paraphrasing a source while keeping its sentence structure and most of its words.

## 4. Distinctive-phrase external search
- **How:** `--distinctive N` emits N spread-out long phrases; search each on the web and via `find-papers` (Semantic Scholar) for verbatim hits.
- **Catches:** overlap with sources you didn't think to supply, when the phrasing is distinctive enough to be searchable.
- **Blind to:** paywalled text not indexed by the searched engines (the core reason this is not a publisher-grade scan).

## 5. Common-knowledge vs needs-citation
- **How:** flag specific factual/empirical claims stated without a citation that a reviewer would expect one for; hand the specifics to `verify-citations`.
- **Catches:** the *under*-citation failure mode (presenting others' findings as your own by omission), which is plagiarism-adjacent.

## Aggregation & severity
- **Critical:** multi-sentence verbatim copy from an external source with no quotation/citation.
- **High:** substantial self-recycling; close paraphrase of a key passage.
- **Medium:** short uncited overlaps; distinctive phrase with an external match to verify.
- **Low:** common phrasing flagged by the shingler (dismiss with a note).
- Every report states the **scope limitation** (sources checked only; not a full database scan) so a clean result is never oversold.
