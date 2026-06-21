# Format (b): OpenReview threaded responses under character budgets

For venues whose profile says `review.rebuttal_format: openreview-thread`
— NeurIPS, ICML, ICLR and most ML venues. The canonical constraint is
NeurIPS's **10,000 characters per per-review response** (plain text with
markdown, no file uploads). Budgets, phase structure, and upload rules
change per cycle: re-verify on the live CFP/handbook via the profile's
`cfp_url` and the instructions in the review-release email, which override
everything.

## Contents

- [Thread mechanics](#thread-mechanics)
- [What counts against the budget](#what-counts-against-the-budget)
- [Drafting layout](#drafting-layout)
- [Structure of one per-review response](#structure-of-one-per-review-response)
- [The global response](#the-global-response)
- [Budget engineering](#budget-engineering)
- [Discussion-phase etiquette](#discussion-phase-etiquette)
- [Threaded-response checklist](#threaded-response-checklist)

## Thread mechanics

- Each review is a forum note; the author response is posted as a comment
  **threaded under that specific review** — one response per review, plus
  (at most venues) an optional top-level comment visible to all reviewers
  and ACs for global remarks.
- The character limit applies **per response box**, not per paper. A reply
  to a follow-up comment is a new box with its own budget.
- Markdown is supported (NeurIPS-style: markdown + LaTeX math via MathJax
  in most OpenReview venues — verify math rendering in the preview before
  posting). No file uploads; no new PDFs (NeurIPS 2026 explicitly: no
  external links except anonymized code shared with ACs where permitted).
- Rebuttals at NeurIPS-style venues run in phases (2026: response viewing,
  then rolling author–reviewer–AC discussion until `rebuttal_end`, then
  reviewer–AC-only discussion). After the author window closes you cannot
  add anything — front-load substance.
- Anonymity persists: third-person self-citation, no identifying links.

## What counts against the budget

Every character you paste into the box: markdown syntax, spaces, newlines,
LaTeX in `$...$`. The skill's checker counts exactly this way:

```
python3 skills/write-rebuttal/scripts/check_budget.py text responses.md \
    --sections --venue venues/conferences/neurips-2026.yml
```

`--sections` treats each `## ` heading as one response box and excludes
the heading line itself (it usually goes into the comment's title field —
if your venue's form has no title field, budget ~60 extra characters per
response for an inline bold header). The `--venue` flag reads the numeric
limit out of the profile's `review.rebuttal_limit`; `--limit N` overrides.
Exit 1 means at least one box is over.

## Drafting layout

Draft all responses in ONE markdown file, one `## ` section per response
box, so the checkers can run on it:

```markdown
## Global response (top-level comment)
...

## Response to Reviewer gXk2 (R1)
...

## Response to Reviewer 7Pqd (R2)
...
```

Map OpenReview's random reviewer codes to matrix IDs once, at the top of
the triage matrix (R1 = gXk2, ...), and use both in headings so nothing is
misposted. The user posts each section into the matching box by hand —
never post on the user's behalf.

## Structure of one per-review response

1. **One-line opener**: thanks + the response's map. "We thank R2 for the
   careful review; we address the novelty concern (R2.3), the ablation
   (R2.1), and clarity points below."
2. **Point-by-point**, each opened by a bold abridged quote with the
   matrix ID:

   ```markdown
   **[R2.1] "the ablation does not isolate component X"**
   Rows 3 vs. 5 of Table 4 differ only in X (Sec. 6.2, L412). We will
   reorder the table so the pair is adjacent.
   ```

3. Highest-severity point first — reviewers often read only the top of a
   response before the discussion phase.
4. **One-line closer with the ask**: "We hope these clarifications address
   the concerns and would appreciate it if the reviewer reconsidered the
   score." Direct but not demanding.

## The global response

Use the top-level comment when (a) two or more reviewers share a concern —
answer it once there, and in each per-review response write one line
pointing to it ("see shared point S1 in the global response"); or (b) you
have permitted new results to report once. Keep it under ~2,500 chars; ACs
read it first. If nothing is shared, skip it.

## Budget engineering

When a section comes back OVER from `check_budget.py`, trim in this order:

1. Cut courtesy beyond the opening line; cut restatements of the review.
2. Abridge reviewer quotes to the load-bearing clause.
3. Replace explanation with anchors: "see Sec. 4.3, L231" instead of
   re-deriving.
4. Move shared material to the global response and link to it.
5. Convert requested numbers to a markdown table (denser than prose).
6. Compress markdown overhead: `**[R2.1]**` headers instead of `###`
   blocks, single newlines between points.
7. If still over, cut the weakest low-severity response to one clause
   ("R2.5: agreed, fixed") — never cut a high-severity answer to fit a
   low-severity one.

Re-run the checker after each pass; also run coverage:

```
python3 skills/write-rebuttal/scripts/check_coverage.py points.md responses.md --strict
```

## Discussion-phase etiquette

- Respond to reviewer follow-ups within a day where possible; silence in
  the discussion phase reads as concession.
- Each follow-up reply is a fresh budget — do not pad; answer the delta.
- If a reviewer acknowledges a point is resolved, do not relitigate it.
- If a reviewer goes silent after your response, one polite nudge near the
  deadline is acceptable, addressed to the points: "As the discussion
  period closes, we would appreciate the reviewer's view on whether our
  response to R2.1/R2.3 resolves the concerns."
- Never argue scores with the AC directly; summarize resolved/unresolved
  points neutrally if an AC asks.

## Threaded-response checklist

- [ ] Live CFP/handbook re-verified: per-response character limit, phase
      dates, link/upload policy
- [ ] One `## ` section per response box; reviewer code ↔ matrix ID map
      recorded
- [ ] Every triaged point covered (`check_coverage.py` exit 0)
- [ ] Every response anchored to paper sections/tables/lines
- [ ] All boxes within budget (`check_budget.py text --sections` exit 0)
- [ ] New numbers (if any) actually produced, permitted by venue policy,
      and labeled as new
- [ ] No external links; anonymity preserved
- [ ] User posts the responses themselves — nothing submitted on their
      behalf
