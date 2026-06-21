# Clustering prior work and articulating deltas

How to turn a pile of retrieved papers into a Related Work section that
positions the paper instead of summarizing the field.

## Table of contents

1. [What a Related Work section is for](#what-a-related-work-section-is-for)
2. [Required clusters from claimed scope](#required-clusters-from-claimed-scope)
3. [The coverage gate and gap routing](#the-coverage-gate-and-gap-routing)
4. [Choosing the clustering axis](#choosing-the-clustering-axis)
5. [The per-cluster paragraph pattern](#the-per-cluster-paragraph-pattern)
6. [Articulating the delta](#articulating-the-delta)
7. [The closest competitor gets its own paragraph](#the-closest-competitor-gets-its-own-paragraph)
8. [Comparison tables](#comparison-tables)
9. [Concurrent and very recent work](#concurrent-and-very-recent-work)
10. [Length and citation budgets](#length-and-citation-budgets)
11. [Anti-patterns reviewers punish](#anti-patterns-reviewers-punish)
12. [Rewrite procedure for an existing laundry list](#rewrite-procedure-for-an-existing-laundry-list)

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

## Required clusters from claimed scope

The most common silent failure is letting the *retrieved corpus* decide the
section's structure. `find-papers` returns what a query happened to surface;
if you cluster only that pile, the outline positions confidently against
retrieved-but-peripheral work while leaving a structural hole exactly where
the paper lives — the direct competitor never queried, the foundational
lineage the sub-area is built on, a whole expected sub-area with zero
citations. Reviewers read that hole as "the authors don't know their own
neighbourhood." Recurring real shapes: a modality-benchmark cluster missing
its named direct prior; an accessibility/application neighbourhood absent
entirely; a deep-structure or scale-space lineage with no canonical anchor; a
covariate-shift variant cited without its base method; a robust-aggregation
family represented by one paper; a frontier sub-area's last two years missing.

The fix is to derive the clusters the section MUST contain from the paper's
*own claimed scope*, before and independently of retrieval:

1. **Enumerate the claimed scope.** From the brief/intro/abstract, list every
   contribution, sub-task, and stated requirement (modality handled, setting,
   guarantee, deployment constraint). One line each.
2. **For each, name the required clusters — citation-free at this stage:**
   - a **direct-prior-approach** cluster: the line of work that already
     attacks *this* sub-task (the competitors a reviewer expects you to beat
     or build on). At least one per contribution.
   - a **foundational-lineage / canonical-anchor** check: the originating
     method or canonical result the sub-area rests on. Cite the origin of an
     idea, not only the latest refinement — a cluster that skips its anchor
     reads as unaware of the field.
   - optionally **adjacent** clusters a reviewer would expect to see
     distinguished (neighbouring problems, alternative settings).
3. **Mark each cluster `expected`** when a competent reviewer would notice it
   missing. These are the ones whose absence is a reject risk, not a stylistic
   choice.

This list is the *target structure*. It generalizes across papers and venues
precisely because it is generated from the claim, not from whatever a search
returned. Only after it exists do you map the retrieved pool onto it (next
section). Driving structure from scope is what converts "we cited what we
found" into "we covered what the paper requires."

Keep the target honest: do not invent a cluster the paper does not actually
need to position against just to look thorough — that is survey drift. The
test is "would a reviewer fault its absence?", not "does the area exist?".

## The coverage gate and gap routing

Once the required clusters exist and the pool is retrieved, assign each
retrieved paper to a required cluster and run the gate deterministically:

```
python3 scripts/check_coverage.py plan.json    # or the text form; see --help
```

The plan lists one block per required cluster with the verified cite keys
assigned to it. The script applies two thresholds:

- **Citation floor (per cluster, default 2):** a cluster below the floor
  WARNs. A cluster resting on a single citation is a reviewer target — one
  paper cannot characterize a "line of work."
- **Zero-citation FAIL:** a required cluster with no citations is a blocking
  structural hole. The script exits 3 and emits a *second-pass retrieval
  worklist*.

Routing the gap (the part that matters):

- A failing or thin required cluster is **not** an author to-do to bury in the
  draft. Take the worklist back to `find-papers` as a targeted second pass
  (scoped to that cluster's sub-task and the venue's norms), retrieve, verify,
  re-assign, and re-run the gate.
- Repeat until every required cluster clears the floor, OR the user explicitly
  accepts a documented thin/empty cluster (e.g. the sub-area genuinely has no
  prior work — a real "first to X under constraint Y", stated as such). That
  acceptance is the user's call, surfaced — never the skill's silent default.
- Never close a hole by stretching an adjacent cluster to pretend coverage, or
  by deleting the contribution from the claimed scope to make the gap vanish.

Only a cleared gate (or an explicitly accepted exception) licenses drafting
prose. This is the anti-structural-hole counterpart to the anti-hallucination
audit: `check_coverage.py` guards what's *missing*, `audit_bib.py` /
`verify-citations` guard what's *present*.

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

- **Calibrate to the venue's measured exemplar median, not to maximal
  coverage.** Read the target profile's `exemplar_distribution` (its
  `related_work` band when present, else `refs_per_page` × the section's page
  budget); when no on-family distribution is recorded, measure 3–5 recent
  accepted papers via `study-exemplars`. The numbers below are a fallback
  prior, not a target to max out — over-citing to look thorough reads as
  survey drift, and a section much longer than the venue's exemplars signals
  an author who mistakes coverage for positioning.
- Conference papers (10–12 page venues): 0.5–1 page, typically 15–40
  references engaged in Related Work. 4-page short/demo papers: one tight
  paragraph to half a page.
- ML venues (9-page NeurIPS-style): often 0.3–0.6 page in the main body.
- CHI/HCI and journals: materially longer (often 1.5+ pages) with deeper
  per-work engagement — see placement-conventions.md.
- The required-cluster floor and the exemplar median are complementary
  bounds: the floor sets the *minimum* breadth (no expected cluster empty, no
  cluster on one citation), the median caps the *maximum* (do not balloon past
  what the venue's strong papers do). Aim between them.
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
| Structural hole | A direct competitor / canonical lineage / whole expected sub-area is simply absent; the corpus drove the structure | Derive required clusters from claimed scope; `check_coverage.py` FAILs the empty cluster; route to `find-papers` |
| Cluster-on-one-citation | A "line of work" represented by a single paper | Citation floor (≥2) via `check_coverage.py`; second-pass retrieval or merge |
| Survey drift | Section reads as a mini-survey of the area | Cut anything that does not sharpen a delta or pre-empt a reviewer; cap length at the venue's exemplar median |

## Rewrite procedure for an existing laundry list

1. Derive the required clusters from the paper's claimed scope FIRST (§
   Required clusters from claimed scope) — independently of what the existing
   section happens to cite. This is the structure the rewrite must hit; the
   old section's citation list is evidence, not the target.
2. Extract every cited work from the section (`scripts/audit_bib.py` gives
   the key list; the worksheet from `gather_candidates.py` gives metadata).
3. Map the existing citations onto the required clusters — do not discard any
   yet. Existing clusters that match no required cluster are candidates to cut
   (survey drift); required clusters that no existing citation fills are the
   holes the laundry list was masking.
4. Run the coverage gate (`check_coverage.py`): every empty/thin required
   cluster's worklist goes to `find-papers` for a targeted second pass.
   Singleton clusters → fill to the floor, merge, or cut. Re-run until clear.
5. Write the new section from the cluster plan (pattern above), reusing
   accurate characterizations from the old text, calibrated to the venue's
   exemplar median.
6. Diff old vs new citation sets for the user: dropped (and why), added
   (and from where they were retrieved). Dropped citations are a user
   decision, not a silent one.
7. Audit + verify (SKILL.md audit and verify-citations steps).
