# "Questions you hope nobody asks" — the dreaded-question inventory

The highest-value 20 minutes of Q&A prep: enumerate the questions the
speaker is afraid of, and build an honest answer for each *before* someone
asks it with 200 people watching. Fear of a question is almost always fear
of an unprepared answer — preparation, not spin, removes it.

## Contents

- [The honesty rule](#the-honesty-rule)
- [Where dreaded questions hide (mining checklist)](#where-dreaded-questions-hide-mining-checklist)
- [The prep template (one card per question)](#the-prep-template-one-card-per-question)
- [Worked example](#worked-example)
- [Drilling the inventory](#drilling-the-inventory)

## The honesty rule

This prep builds **honest answers to hard questions** — never wording that
hides, minimizes, or misrepresents a limitation. If the user asks for an
answer that conceals a known weakness ("how do I avoid admitting we only
used one dataset?"), decline that framing and coach the honest version:
the concede-and-scope answer is also, conveniently, the one that performs
best in a room full of reviewers. Weaknesses that turn out to be fixable
before the talk (a missing experiment, an overdrawn claim on a slide) are
better fixed than rehearsed — say so.

## Where dreaded questions hide (mining checklist)

Go through the paper and slides with the user and harvest from each
location. Aim for 8–15 questions; rank by (probability x damage).

1. **The limitations section** — every sentence there is a question someone
   will ask out loud, usually less politely than it was written.
2. **The claim inventory** — every "first", "state-of-the-art",
   "outperforms", "real-world": what is the weakest link between that claim
   and its evidence? (Reuse the claim inventory from `simulate-reviewers`
   if one exists.)
3. **Experimental scope** — single dataset? proprietary data? one seed? no
   significance tests? missing well-known baseline? small N? short
   time horizon?
4. **The "why not the obvious thing" question** — why not the simpler
   method, the standard benchmark, the existing tool? If the honest answer
   is "we didn't think of it" or "deadline", prepare the honest version:
   "we haven't compared yet; it's the immediate next experiment."
5. **Assumptions** — which assumption, if dropped, kills the result? What
   happens at the boundary?
6. **What was cut** — experiments that failed, datasets dropped, the
   reviewer concern from the rebuttal that never fully resolved. The
   rebuttal file is a goldmine: real reviewers already asked the dreaded
   questions once.
7. **Concurrent and prior work** — the scooped-by question: "how is this
   different from <the recent similar paper>?" Identify the real closest
   work with `find-papers`, verify it with `verify-citations`, and rehearse
   the one-sentence delta. Never prep against an invented citation.
8. **Numbers that look odd** — the metric that dips in one column, the
   suspiciously round number, the baseline that beats you on one dataset.
   Assume the sharpest person in the room saw it.
9. **Ethics, data provenance, and AI use** — consent/IRB for collected
   data, licensing of scraped data, dual-use potential, "did an LLM write
   this?" (answer must match the venue's disclosure policy and the paper's
   own statements).
10. **Authorship and credit** — for defenses and job talks: "which part is
    *your* contribution?" Rehearse a precise, generous, honest answer.
11. **Reproducibility** — "can I run this tonight?" If the code is not
    released, the honest status and reason, not a promise that slips.
12. **The career question** (defense/job talk) — "where does this go in
    5 years?", "what would you do with twice the compute?", "what's the
    weakest part of the thesis?" The last one is a trap for the
    unprepared and a gift for the prepared.

## The prep template (one card per question)

For each dreaded question, build a card:

```
Q: <the question, phrased as bluntly as a hostile asker would>
Probability: high | medium | low      Damage if fumbled: high | medium | low
Honest core: <the true state of affairs, one sentence, no spin>
Headline answer: <first sentence, answer-first, commits immediately>
Evidence: <the one number/experiment/argument that supports the headline>
Scope/concession: <what we genuinely don't know or didn't do — said plainly>
Do NOT say: <the overclaim or defensive move to avoid>
Fix instead? <if addressable before the talk: fix the slide/claim, don't rehearse around it>
```

The card's first sentence gets memorized verbatim (especially valuable for
non-native speakers); the rest is structure, not script.

## Worked example

Paper: trajectory-imputation model, evaluated on one proprietary taxi
dataset, no code release.

```
Q: All your results are on one private dataset nobody can check — why
   should anyone believe them?
Probability: high      Damage if fumbled: high
Honest core: evaluation breadth is the paper's weakest point; we mitigated
  but did not remove it.
Headline answer: "You're right that it's one dataset, and that's the main
  limitation — two things make me confident it isn't an artifact."
Evidence: results hold across all 12 city districts and three gap regimes
  within the data; we release a synthetic generator matching the data's
  statistics so the pipeline itself is checkable.
Scope/concession: cross-city generalization is untested; it is the first
  item of future work, not a claim we make.
Do NOT say: "the dataset is large, so it generalizes" (non sequitur);
  anything implying the data could be shared when it can't.
Fix instead? if a public dataset run is feasible before the talk, run it —
  this card then becomes a strength.
```

## Drilling the inventory

- The drill plan (`qa_drill.py`) reserves a **dreaded-question finale**
  round: ask the top cards in persona, hardest last.
- A card passes only when the spoken answer (a) opens with the headline,
  (b) includes the concession unprompted, and (c) lands under the time cap
  (`grade_answers.py` on the transcript).
- Re-drill failed cards later in the same session — an answer is drilled
  when it lands twice.
- Output the final inventory as a crib sheet the user can review the
  morning of the talk: question → memorized headline → one number.
