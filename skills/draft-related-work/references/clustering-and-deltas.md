# Clustering prior work and articulating deltas

How to turn a pile of retrieved papers into a Related Work section that
positions the paper instead of summarizing the field.

## Table of contents

1. [What a Related Work section is for](#what-a-related-work-section-is-for)
2. [Choosing the clustering axis](#choosing-the-clustering-axis)
3. [The per-cluster paragraph pattern](#the-per-cluster-paragraph-pattern)
4. [Articulating the delta](#articulating-the-delta)
5. [The closest competitor gets its own paragraph](#the-closest-competitor-gets-its-own-paragraph)
6. [Comparison tables](#comparison-tables)
7. [Concurrent and very recent work](#concurrent-and-very-recent-work)
8. [Length and citation budgets](#length-and-citation-budgets)
9. [Anti-patterns reviewers punish](#anti-patterns-reviewers-punish)
10. [Rewrite procedure for an existing laundry list](#rewrite-procedure-for-an-existing-laundry-list)

## What a Related Work section is for

A Related Work section answers exactly one question for the reviewer:
*given everything that exists, why does this paper need to exist?* It is an
argument, not a survey. Every sentence either (a) characterizes a body of
prior work accurately, or (b) states what that body does not do that this
paper does. A reader should finish the section able to repeat the paper's
positioning in two sentences.

Corollary: prior work is selected for relevance to the claim, not for
completeness. Completeness is the job of `literature-review`; here, a paper
earns a citation by sharpening the delta (or by being something a likely
reviewer would notice missing).

## Choosing the clustering axis

Cluster along the dimension that makes this paper's gap visible. The three
standard axes:

| Axis | Cluster examples | Use when the contribution is... |
|---|---|---|
| **By problem** | "trajectory similarity", "sub-trajectory search", "trajectory clustering" | a new problem or problem variant |
| **By technique** | "metric-learning methods", "RNN encoders", "transformer encoders" | a new technique for a known problem |
| **By assumption / setting** | "assume clean GPS", "assume road-network matching", "streaming setting" | removing an assumption, new setting, new constraint (privacy, scale, latency) |

Rules of thumb:

- **3–6 clusters.** Fewer than 3 means the axis is too coarse to show a gap;
  more than 6 reads as a survey and blows the page budget.
- The paper itself must NOT fit cleanly into any cluster — if it does, the
  axis hides the contribution; pick another axis. The gap should be visible
  as "no cluster covers the intersection we handle".
- Clusters are allowed to overlap in membership (a paper can be cited in
  two clusters with different one-clause characterizations), but keep this
  rare.
- Outliers that fit no cluster but a reviewer would expect: either a short
  "other related directions" closing cluster, or a single sentence attached
  to the nearest cluster. Never force a fake theme around one paper.
- Name clusters with `\paragraph{...}` or bold lead-ins when the venue's
  papers do (check exemplars); otherwise make the first sentence of each
  paragraph do the naming.

Work on the worksheet from `scripts/gather_candidates.py`: fill the
`cluster:` slot for every candidate, then the `delta:` slot per cluster, and
only then write prose. Papers that end up in no cluster and serve no
reviewer-expectation purpose get cut — do not cite for volume.

## The per-cluster paragraph pattern

One paragraph per cluster, four moves, in order:

1. **Claim sentence** — name the cluster and its shared goal/approach.
   *"A first line of work computes trajectory similarity with learned
   embeddings."*
2. **Representative works** — 2–6 citations, each with at most one clause of
   characterization. Group minor variants: *"...using RNN encoders [12, 17],
   later transformers [3]."* Cite the ORIGIN of an idea, not only the latest
   refinement.
3. **Limitation w.r.t. this paper's problem** — what the whole cluster does
   not handle. Must be true of the cluster, checkable, and *relevant* — a
   limitation the paper does not address is padding.
4. **Delta sentence** — what this paper does about it. *"In contrast, our
   index supports sub-trajectory queries without re-embedding, which no
   embedding-based method supports."*

The paragraph should survive the "so what" test: delete it and the paper's
positioning gets weaker, or the paragraph was filler.

## Articulating the delta

A delta is a precise difference along a named dimension, not an adjective.
Usable dimensions: problem definition, input assumptions, guarantee
(exact/approximate, worst-case), supported operations, scale, data modality,
supervision required, evaluation regime, deployment constraint.

Phrasing patterns that work:

- *"These methods require X; we remove that requirement by Y."*
- *"[12] optimizes A under assumption B; our setting drops B, which breaks
  their core invariant (Section 3)."*
- *"Unlike [3, 7], which answer whole-object queries, we support Z."*
- *"Our approach is complementary: it can run on top of any method in this
  family, and we evaluate with [12] as the backbone (Section 5)."* —
  complementarity is a legitimate delta; not everything must be beaten.

Honesty rules:

- Every limitation claim must be verifiable against the cited paper's actual
  content (you retrieved the metadata/abstract — when in doubt, read the
  paper via `fetch-paper` before asserting what it cannot do).
- Avoid bare "first to X" claims; they are falsified by a single reviewer
  counterexample. Scope them: *"to our knowledge, the first to X under
  constraint Y"* — and only after a genuine search for X.
- "Their method is slow/simple/naive" is not a delta. "Their method is
  quadratic in trajectory length (their Section 4.2); ours is linear" is.
- If the honest delta is small, say it plainly and lean on the empirical
  comparison. Reviewers forgive modest deltas; they do not forgive inflated
  ones.

## The closest competitor gets its own paragraph

Identify the single closest prior paper — the one a reviewer would name in
"how is this different from ___?" — and give it dedicated treatment, usually
at the end of the section:

- State precisely what it does, in its own terms (the author may review you).
- State 2–3 concrete distinctions (dimension + consequence each).
- Point to where the paper substantiates them (*"Section 5.3 compares
  directly"*). If there is no direct empirical comparison, flag that to the
  user now — reviewers will ask.

Pretending the closest competitor is just another cluster member is the most
common positioning failure; reviewers read it as either ignorance or evasion.

## Comparison tables

Add a feature-comparison table only when ALL hold: ≥3 clusters or systems,
≥3 binary/short-valued comparison dimensions, and the table's last row
(this paper) is not all-checkmarks-by-construction with dimensions chosen to
flatter it — include at least one dimension where prior work wins or ties,
or reviewers discount the table. Keep it to half a column. LaTeX sketch
(booktabs, no vertical rules):

```latex
\begin{table}
  \caption{Prior work vs. this paper. \cmark{}=supported.}
  \label{tab:relwork}
  \begin{tabular}{lccc}
    \toprule
    Method & Sub-traj. & Streaming & Exact \\
    \midrule
    EmbedSim~\cite{li2018deeplearning} & \xmark & \cmark & \xmark \\
    SeedMetric~\cite{yao2019computing} & \xmark & \xmark & \xmark \\
    \textbf{Ours} & \cmark & \cmark & \xmark \\
    \bottomrule
  \end{tabular}
\end{table}
```

Every cell is a claim — each must be checkable against the cited paper.

## Concurrent and very recent work

- Work published or preprinted within ~3 months of submission (or after the
  venue's stated cutoff) is *concurrent*: cite it, note "concurrent work",
  describe the difference, and do not claim superiority over it without
  evidence. Many venues' policies state concurrent work cannot be held
  against a submission — but ignoring a well-known concurrent preprint
  still costs reviewer goodwill.
- arXiv-only papers: cite with the arXiv ID; when a published version
  exists, cite the published venue instead (`verify-citations` flags these).

## Length and citation budgets

- Conference papers (10–12 page venues): 0.5–1 page, typically 15–40
  references engaged in Related Work. 4-page short/demo papers: one tight
  paragraph to half a page.
- ML venues (9-page NeurIPS-style): often 0.3–0.6 page in the main body.
- CHI/HCI and journals: materially longer (often 1.5+ pages) with deeper
  per-work engagement — see placement-conventions.md.
- Sentence-per-citation ratio: most citations get a clause, not a sentence;
  only cluster representatives and the closest competitor get full
  sentences. If every citation has its own sentence, it is a laundry list.
- The section competes with Method/Evaluation for the page budget. When the
  draft is over budget, Related Work is compressed by merging clusters and
  tightening characterizations to clauses — never by deleting the deltas.

## Anti-patterns reviewers punish

| Anti-pattern | Symptom | Fix |
|---|---|---|
| Laundry list | "X et al. proposed... Y et al. proposed..." with no grouping | Re-cluster; one paragraph per theme |
| Annotated bibliography | Each paper gets 2–3 descriptive sentences, no comparison | Compress to clauses; spend the saved words on deltas |
| Missing delta | Clusters described, "our work is different" asserted once at the end | One explicit delta sentence per cluster |
| Strawman | Prior work characterized as weaker than it is | Restate each limitation from the cited paper's own scope |
| Citation dump | `[3,5,8,11,14,19]` with no characterization | Pick 2–3 representatives, cut or group the rest |
| Checkmark-inflation table | Comparison table where only "Ours" has all checkmarks on hand-picked dimensions | Add dimensions where prior work wins; or cut the table |
| Closest competitor buried | The obvious rival appears mid-list with one clause | Dedicated paragraph with concrete distinctions |
| Self-citation overload | Author's own prior papers dominate clusters | Cite own work only where genuinely load-bearing; voice per blind level |
| Unverified citations | Entries with no DOI/arXiv ID, plausible-sounding titles | `audit_bib.py` flags them; verify or remove |
| Survey drift | Section reads as a mini-survey of the area | Cut anything that does not sharpen a delta or pre-empt a reviewer |

## Rewrite procedure for an existing laundry list

1. Extract every cited work from the section (`scripts/audit_bib.py` gives
   the key list; the worksheet from `gather_candidates.py` gives metadata).
2. Cluster the existing citations first — do not discard any yet.
3. Find the gaps: clusters a reviewer would expect that have no members →
   run `find-papers` to fill them; singleton clusters → merge or cut.
4. Write the new section from the cluster plan (pattern above), reusing
   accurate characterizations from the old text.
5. Diff old vs new citation sets for the user: dropped (and why), added
   (and from where they were retrieved). Dropped citations are a user
   decision, not a silent one.
6. Audit + verify (SKILL.md steps 6–7).
