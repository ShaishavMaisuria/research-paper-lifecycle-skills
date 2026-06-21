# Resize tactics: where length hides, and how to add it well

Use this reference after the section-budget map identifies where the words are.
The skill chooses tactics based on whether the paper is over or under the
target length.

## Compress: ranked by safety

Cut in this order. Earlier items are safer because they remove less information.

1. **Redundancy across sections**: a contribution restated in abstract, intro,
   method, and conclusion. Keep the strongest statement and delete the echoes.
2. **Verbose related work**: replace paragraph-per-paper prose with grouped
   sentences that state only the delta to this work.
3. **Walkthroughs a figure already shows**: if a figure or algorithm conveys
   it, the prose can shrink to a pointer.
4. **Wordiness**: hand to `polish-prose`; remove throat-clearing, nominalized
   phrasing, and double hedges.
5. **Setup/background the venue audience already knows**: trim common
   preliminaries to a citation.
6. **Move to appendix**: proofs, extra experiments, hyperparameter tables, or
   implementation details. This only helps if the venue excludes the appendix
   or supplementary material from the limit; verify first.
7. **Figures and tables**: use `polish-tables-figures` to resize, merge
   subfigures, drop redundant baseline columns, or switch a large table to a
   compact plot.
8. **Layout within the rules**: use compact legal structure such as
   `\paragraph{}` instead of a full subsection. Never shrink margins, fonts, or
   spacing to evade the template.

Hard line: if the paper still will not fit, the honest move is to cut scope: a
weaker contribution or a secondary experiment. Tell the author and let them
decide. Never delete reported results, evidence for a claim, or citations just
to make the page count.

## Expand: substance only

Rank additions by how much they strengthen the paper, not by how many words
they add.

1. **Ablations**: often the most valuable missing evidence at empirical venues.
2. **Error or failure analysis**: show where and why the method fails.
3. **Limitations or threats to validity**: concrete limits, not a generic
   humility paragraph.
4. **Deeper analysis of existing results**: explain what the numbers mean.
5. **Clearer motivation or a worked example**: useful when reviewers may not
   feel the problem quickly enough.
6. **A related-work gap**: only if a genuinely relevant cluster is missing; use
   `find-papers` and `verify-citations` before adding it.

Never pad: no restating the intro at length, no filler figures, and no spacing
games. If none of the above genuinely applies, advise leaving the paper short.
