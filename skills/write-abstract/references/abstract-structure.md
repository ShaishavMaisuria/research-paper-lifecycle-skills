# The five-move abstract: motivation → gap → approach → results → impact

How to draft and critique a CS-paper abstract sentence by sentence. The
moves are a planning device, not headings — a good abstract reads as one
seamless paragraph.

## Contents

- [The five moves](#the-five-moves)
- [The typed result slot](#the-typed-result-slot)
- [Budgeting words across moves](#budgeting-words-across-moves)
- [Family tone differences](#family-tone-differences)
- [Anti-patterns](#anti-patterns)
- [A drafting procedure](#a-drafting-procedure)

## The five moves

| # | Move | Job | Typical openers (vary them) |
|---|---|---|---|
| 1 | Motivation | Why the problem matters, for whom | "X is a foundational primitive in...", "Modern Y systems must..." |
| 2 | Gap | What existing work cannot do, precisely | "However, existing approaches assume...", "...fails when..." |
| 3 | Approach | The named contribution and its one key idea | "We present NAME, a ... that ..." |
| 4 | Results | The strongest *quantified* evidence | "On N datasets, NAME achieves ...", "...2.4x higher throughput" |
| 5 | Impact | Why a reader should care beyond the numbers | "These results suggest...", "Code and data are available..." |

Rules per move:

1. **Motivation** — one or two sentences, concrete, no textbook platitudes
   ("X has attracted much attention" says nothing). Name the workload,
   user, or system that hurts.
2. **Gap** — the most important sentence in the abstract. State the
   *specific* failing assumption or missing capability, not "prior work is
   limited". The gap must be exactly the thing the approach fixes.
3. **Approach** — name the system/method once, then give the single
   technical idea that makes it work. Resist listing every component; the
   intro does that.
4. **Results** — the single most-predictive surface of the abstract: a
   reviewer skims here first and the results→impact arc cannot score in the
   top band without it. Use real numbers from the paper's evaluation. NEVER
   invent, round up, or extrapolate numbers: pull them from the draft or ask
   the user. If results are not final, leave exactly ONE **typed
   quantified-result slot** (see [the typed result slot](#the-typed-result-slot)
   below) — never bare `[RESULT: ...]` and never placeholder prose that
   could be mistaken for a finding (and never register a placeholder
   abstract; see [venue-norms.md](venue-norms.md)).
5. **Impact** — one sentence. Generalization, artifact availability
   ("code is open source" — but check the blind level before naming a URL),
   or the door the result opens. Cut this move first when over budget.

## The typed result slot

When results are not yet final, the abstract still must keep its
results→impact arc structurally complete. Do this with a **typed
quantified-result slot**: exactly one designated slot, written as a
structured contract rather than free text, so it is trivially fillable later
and a machine can tell whether it is bound.

The contract carries four parts:

| Part | What it pins down | Example token |
|---|---|---|
| Metric name | which measure is reported | `Recall@20`, `p99 latency`, `BLEU` |
| Units | how it is denominated | `%`, `pp` (percentage points), `ms`, `×` |
| Sign / direction | improvement vs regression, up vs down | `+`, `−`, "higher", "lower" |
| Comparison target | what it is measured against | `vs best hashing baseline`, `over SOTA`, `relative to prior under matched budget` |

Write the slot as a single bracketed contract, not prose:

```
... NAME achieves [RESULT: +XX% Recall@20 vs best hashing baseline under matched budget].
```

Rules:

- **Exactly one** RESULT slot per abstract. Secondary numbers live in the
  body, not the abstract; if you have two headline numbers, pick the one a
  reviewer would quote and merge the rest.
- **Typed, never bare.** `[RESULT: ...]`, `[RESULT: substantially better]`,
  or "significantly outperforms prior work" are all rejected by the linter:
  they leave the most-predictive surface incomplete and unfillable. The
  comparison target is mandatory — a number with no baseline does not score.
- **A bracketed slot is never submittable.** Even a fully-typed
  `[RESULT: +12% Recall@20 vs ...]` is treated as an *open slot* until you
  replace the bracket with the verified number written into the prose. The
  linter counts open slots and **hard-fails** (non-zero exit, independent of
  `--strict`) while any remain — the abstract is DRAFT-not-submittable.
- **Fill it from the evaluation, never invent it.** When the real number
  arrives, drop the brackets and the `RESULT:` label and bind the value into
  the sentence; keep the metric/units/sign/target the contract already named.
- Use the same `[LABEL: ...]` form for any other deferred fact
  (`[CONFIRM: which workload?]`); every such slot is counted and gates
  submission the same way.

## Budgeting words across moves

For a 150-250 word abstract (the dominant norm — see
[venue-norms.md](venue-norms.md)):

- Motivation 15-20%, Gap 15-20%, Approach 30-35%, Results 20-25%, Impact 5-10%.
- One move per 1-2 sentences; 6-9 sentences total; keep every sentence
  under ~40 words (the linter flags longer ones).

## Family tone differences

- **ML (NeurIPS-style: NeurIPS/ICML/ICLR/CVPR/AAAI)** — "one paragraph";
  no in-paper keywords. Benchmarks and deltas carry the abstract; name the
  datasets and the headline metric. Claims of "state of the art" must match
  the tables exactly.
- **Systems/DB (ACM sigconf, IEEE conf: SIGMOD/VLDB/ICDE/KDD/SIGSPATIAL)** —
  throughput/latency/scale numbers expected; name the workload and the
  baseline class beaten. The approach move usually names the system.
- **HCI (CHI manuscript)** — state the study type and N ("a study with 24
  participants"), the method (interview/survey/lab study), and findings as
  insights, not only metrics.
- **Theory / LNCS venues** — results move states the theorem/bound in words
  ("we prove a tight O(n log n) bound..."); quantified experiments optional.
  Length is *mandated* 150-250 words at LNCS.

## Anti-patterns

- Citations (`\cite`) in the abstract — it ships as standalone metadata;
  name the prior work in prose if unavoidable.
- `\ref`/math/URLs — break in HTML/metadata renderings; the linter warns.
- "In this paper" more than once; "novel" anywhere (show, don't label).
- Undefined acronyms beyond universally known ones (GPU, SQL, ML).
- Results vagueness: "significantly outperforms" with no number — and, while
  results are pending, a bare `[RESULT: ...]` instead of the typed slot
  contract ([the typed result slot](#the-typed-result-slot)).
- Identity leaks at double-blind venues: institution names, "our previous
  work [X]", named GitHub orgs.
- Abstract that promises more than the paper's evaluation shows — reviewers
  read the abstract last to check for over-claiming.

## A drafting procedure

1. Extract from the draft (or user): problem, failing assumption of prior
   work, contribution name + key idea, the 1-3 strongest verified numbers,
   artifact status.
2. Write one sentence per move, in order. If results are pending, write the
   results move as exactly one typed slot
   ([the typed result slot](#the-typed-result-slot)); mark any other
   unverifiable fact `[CONFIRM: ...]`.
3. Merge sentences into a paragraph; cut to the venue's word budget
   (cut impact → motivation adjectives → secondary results, in that order).
4. Run the linter (`scripts/abstract_check.py`) and fix RISK/WARN findings.
5. Read it aloud once: every sentence should answer "so what?" for the next.
