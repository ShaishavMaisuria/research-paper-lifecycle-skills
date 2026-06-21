# Hedging calibration and active contribution statements

Companion to `scripts/prose_lint.py` (checks: `double-hedge`, `booster`,
`hedge-inventory`, `passive-contribution`, `significant`). The single rule:
**claim strength must match evidence strength — in both directions.**
Overclaiming gets the paper rejected by reviewers; underclaiming gets it
ignored. LLM drafts reliably do both at once: timid about the contribution,
breezy about the implications.

## Contents

- [The calibration rule](#the-calibration-rule)
- [Where hedges belong — and where they do not](#where-hedges-belong--and-where-they-do-not)
- [The hedge taxonomy](#the-hedge-taxonomy)
- [Double hedges](#double-hedges)
- [Boosters and overclaiming](#boosters-and-overclaiming)
- [The "significant" rule](#the-significant-rule)
- [Active contribution statements](#active-contribution-statements)
- [Limitations: the honest-hedge zone](#limitations-the-honest-hedge-zone)
- [Calibration checklist](#calibration-checklist)

## The calibration rule

For every hedged or boosted sentence ask: *what does the paper's own
evidence support?* Then write exactly that.

- Measured on your benchmark → state it flat: "reduces median latency by
  38% on our three-city workload."
- Expected to generalize but not tested → one hedge, scoped: "we expect
  similar gains on workloads with comparable skew."
- Speculation → label it: "we conjecture...", and put it in discussion or
  future work, not the abstract.

Editing hedges is the one place this skill brushes against meaning, so the
discipline is strict: a hedge may be **moved or deduplicated**, and a
booster may be **deleted**, but the underlying claim is never strengthened
beyond the evidence or weakened below what was measured. Every sentence
whose claim strength changes goes into the step-9 before/after table in
SKILL.md for explicit user sign-off.

## Where hedges belong — and where they do not

| Zone | Hedging | Example |
|---|---|---|
| Contribution statements | None | "We propose X." — you did propose it; there is nothing uncertain about that |
| Definitions, method description | None | "The policy scores tiles by recency." |
| What you measured | None | "Latency drops by 38%." |
| Interpretation of results | One honest hedge | "This suggests the gain comes from skew, not cache size." |
| Generalization beyond the eval | One scoped hedge | "Results may differ for write-heavy workloads." |
| Limitations | Plain statements, not apologies | "We test on three cities; drift is replayed, not live." |
| Related-work comparisons | Careful, factual | "Unlike X, our method does not require offline training." (verify the fact about X before keeping it) |

## The hedge taxonomy

Four families (the linter's `hedge-inventory` counts them):

1. **Modals:** may, might, could, can.
2. **Epistemic verbs:** suggests, indicates, appears, seems.
3. **Approximators:** roughly, somewhat, relatively, to some extent,
   likely, possibly, potentially, arguably.
4. **Attribution shields:** "it is possible that", "one could argue".

A healthy results section uses families 1-3 sparingly and family 4 almost
never. Density alone is not the problem — placement is. Ten hedges in the
limitations section can be honest; two hedges in the contribution list are
self-sabotage.

## Double hedges

Two hedges in one clause say less than one and read as generated text:

| Double | Single |
|---|---|
| "may potentially improve" | "may improve" |
| "could possibly reduce" | "could reduce" |
| "seems to suggest" | "suggests" |
| "it is possible that X might" | "X might" |
| "appears to indicate" | "indicates" |

Keep whichever hedge is more precise; delete the other. Three hedges
("it seems that X could potentially...") collapse the same way.

## Boosters and overclaiming

Clearly, obviously, undoubtedly, certainly, definitely, remarkably,
dramatically, "it is well-known that", "of course":

- If the claim is actually established, cite it (through
  `verify-citations`) — the citation replaces the booster.
- If you measured it, the number replaces the booster ("dramatically
  faster" → "4.1x faster").
- If neither, the booster was hiding a missing argument; flag it to the
  user rather than silently deleting, because the fix is evidence, not
  wording.

"Clearly" and "obviously" deserve special hostility: when true they
insult the reader, when false they insult the paper.

## The "significant" rule

Many reviewers reserve "significant" for statistical significance. The
linter flags `significant` when no statistical-test language appears
anywhere in the draft. Resolutions:

1. You ran a test → report it: "significant (paired t-test, p < 0.01)".
2. You did not → "substantial", "large", or best of all the number itself.
3. Never add test language to justify the word — that would be fabricating
   an analysis, which is a hard stop.

## Active contribution statements

The `passive-contribution` check fires on "a novel X is proposed in this
paper" constructions. Passive contributions read as evasive and bury what
is new. The rewrite recipe:

1. **Subject = the authors.** "We propose / design / prove / measure..."
2. **Verb = what you actually did.** Propose, formalize, implement,
   evaluate — not "explore", "investigate", "attempt" (those are hedged
   verbs pretending to be contributions).
3. **Object = the artifact, named.** Give the system/method its name at
   first mention and reuse it (terminology pass keeps it consistent).
4. **The differentiator, stated plainly.** What is new relative to the
   nearest prior work — one clause, factual, checkable.

> **Before:** A novel caching framework is proposed in this paper, and
> extensive experiments are conducted to demonstrate its effectiveness.
>
> **After:** We propose SkewCache, a tile-caching policy that adapts to
> workload drift without offline retraining; on three city-scale trajectory
> workloads it cuts median latency by 38% over uniform caching.

Notes:

- "novel" is asserted novelty; the differentiator clause *shows* it.
  Delete "novel" almost everywhere.
- Passive voice stays fine in methods/setup ("queries are routed to...")
  where the agent is obvious or irrelevant. The check pairs a passive with
  "this paper/work" precisely to catch contributions, not methods.
- Contribution bullet lists in the introduction follow the same recipe,
  one contribution per bullet, each independently checkable.

## Limitations: the honest-hedge zone

De-AI-ifying must never sand off honesty. LLM drafts often contain
boilerplate limitations ("may not generalize to all scenarios") — replace
them with the real ones, stated flat:

> **Before:** While our approach shows promising results, it may not
> generalize to all possible scenarios and further research is needed.
>
> **After:** We evaluate on three cities with replayed drift; live drift
> and write-heavy workloads are untested. The policy assumes tile-grained
> access; pixel-grained rendering would need a different cost model.

If sharpening a limitation reveals it is worse than the user realized,
that is a finding for the user, not something to soften.

## Calibration checklist

Run after edit pass B (step 6 in SKILL.md):

- [ ] Zero hedges in the contribution statements and definitions.
- [ ] Every measured result stated without hedges, with its number.
- [ ] Every interpretation/generalization carries at most one hedge,
      scoped to what is actually uncertain.
- [ ] Zero double hedges (`prose_lint.py` confirms).
- [ ] Zero boosters, or each remaining one backed by a verified citation.
- [ ] "significant" only with a reported test.
- [ ] Limitations concrete, not boilerplate, not apologetic.
- [ ] Before/after table of every claim-strength change shown to the user.
