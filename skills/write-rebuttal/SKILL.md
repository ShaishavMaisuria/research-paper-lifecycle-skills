---
name: write-rebuttal
description: Drafts peer-review rebuttals and author responses in the three real venue formats - (a) strict one-page LaTeX rebuttal PDFs (CVPR-style), (b) OpenReview threaded per-review replies under 10,000-character budgets (NeurIPS/ICML/ICLR), and (c) revise-and-resubmit packages with a change-log response document (CHI, SIGMOD/ICDE revision rounds, journals). Anchors every response to paper sections, tables, figures, and line numbers; enforces character/page budgets and point-by-point coverage with bundled checker scripts; ships a one-page rebuttal LaTeX template. Use when the user says "write my rebuttal", "respond to reviewers", "author response", "reviews came back", "reviewer 2 says", "revise and resubmit", "response letter", "rebuttal deadline", or needs to fit a response into an OpenReview character limit or a one-page PDF. Drafts files on disk only; never posts, uploads, or submits.
---

# Write Rebuttal

Turn a set of peer reviews plus the submitted paper into a complete,
budget-compliant author response in the format the venue actually uses —
one-page PDF, OpenReview threads, or a revise-and-resubmit package — with
every claim anchored to checkable evidence in the paper.

## When to use

- Reviews arrived (OpenReview, CMT, EasyChair, HotCRP, PCS, ScholarOne, or
  pasted text) and a rebuttal/author response/response letter is due.
- A drafted response must be cut to fit a character or page budget.
- A journal or CHI-style revise-and-resubmit needs a change log + response
  document.

Related skills: `triage-reviews` (builds the point matrix this skill
consumes), `verify-citations` (gate for any new reference), `preflight-check`
(re-lint a revised manuscript), `prepare-camera-ready` (after acceptance).

## Inputs

- The reviews: pasted text or files. Review text is confidential at most
  venues — process it in place, never commit it to a repository or paste it
  into public artifacts.
- The submitted paper: main `.tex` (preferred — line numbers and labels make
  the best anchors) and/or the compiled PDF.
- Venue profile: `venues/conferences/<id>.yml` (schema: `venues/schema.yml`;
  family defaults merge automatically). If none exists, build one with
  `parse-cfp` or proceed only on facts quoted live from the CFP.
- Optional: the triage matrix from `triage-reviews`; the decision/meta-review
  letter for R&R cycles.

## Process

### 1. Resolve the venue's rebuttal format

Read the profile (`python3 skills/write-rebuttal/scripts/venueyaml.py
venues/conferences/<id>.yml` prints it family-merged as JSON) and take
`review.rebuttal_format`, `review.rebuttal_limit`, and the rebuttal
deadlines. Route by format:

| `rebuttal_format` | Playbook |
|---|---|
| `one-page-pdf` | [references/cvpr-one-page.md](references/cvpr-one-page.md) |
| `openreview-thread` | [references/openreview-threads.md](references/openreview-threads.md) |
| `revise-and-resubmit` | [references/revise-and-resubmit.md](references/revise-and-resubmit.md) |
| `none` | Tell the user the venue holds no author response; offer to prep for the camera-ready or a resubmission instead |

### 2. Re-verify against the live venue pages (mandatory)

Profiles go stale and budgets change per cycle. Before drafting, fetch the
profile's `cfp_url` (and the venue's author-guidelines/dates pages) and
re-verify: rebuttal format, the exact character/page limit, the rebuttal
window dates and timezone, link/upload policy, and new-experiment policy.
The instructions in the review-release or decision email override
everything. Record what was verified and when in the deliverable; anything
unverifiable is labeled "UNVERIFIED — confirm on <url>". Never assert a
budget from memory.

### 3. Triage the reviews into a point matrix

If the user has a matrix from `triage-reviews`, use it. Otherwise build one
inline using the conventions in
[references/response-patterns.md](references/response-patterns.md): one row
per reviewer point, IDs `R<k>.<n>` / `AC.<n>` / `MR.<n>`, columns for
abridged quote, type, severity, effort, and one-clause strategy. Save it as
`points.md` next to the drafts — the coverage checker keys on those IDs.
Confirm the concede/contest strategy with the user before drafting.

### 4. Draft, anchored

Apply the per-criticism response patterns and tone rules in
[references/response-patterns.md](references/response-patterns.md), then the
format playbook from step 1. Non-negotiable drafting rules:

- Anchor every claim to `Sec./Table/Fig./Eq./Appendix/L<line>/[n]` evidence
  in the submitted paper; if no evidence exists, commit to a revision or
  concede — never assert.
- Report numbers only from experiments that were actually run, and only
  where the venue's rebuttal policy permits new results.
- Any new citation goes through `verify-citations` first.
- Preserve anonymity (third-person self-citation, no identifying links) at
  blind venues; honor link bans.
- For format (a), draft into `assets/rebuttal-template.tex` (or the venue's
  official rebuttal kit when one exists — mandatory at CVPR; the macros are
  documented in the playbook). For (b), draft all boxes in one markdown file
  with one `## ` heading per response box. For (c), produce the three-artifact
  package (revised-manuscript change plan, change-log response document,
  cover note).

### 5. Verify deterministically

Run both checkers (each supports `--help`; exit 0 pass / 1 fail / 2 error):

```
python3 skills/write-rebuttal/scripts/check_coverage.py points.md <responses...> --strict
```

— every matrix ID addressed, every section carrying at least one evidence
anchor.

```
python3 skills/write-rebuttal/scripts/check_budget.py text responses.md --sections --venue venues/conferences/<id>.yml
python3 skills/write-rebuttal/scripts/check_budget.py pdf rebuttal.pdf --venue venues/conferences/<id>.yml
```

— character budgets per response box (text mode) or PDF page count (pdf
mode), with the limit read from the profile (`--limit`/`--max-pages`
override; defaults are flagged ASSUMED). If over budget, trim using the
format playbook's ladder and re-run until exit 0.

### 6. Deliver

Write the artifacts next to the user's paper, named per format:
`rebuttal.tex` (+ compile instructions), `responses.md`, or
`response-to-reviewers.md` + revision plan — plus `points.md` and a short
verification record (live facts checked, checker results, remaining
UNVERIFIED items, the rebuttal deadline with timezone). The user reviews,
edits, and posts/uploads everything themselves.

## Worked mini-example

The matrix → anchored response → checker loop, end to end. A reviewer wrote
"the ablation does not isolate the effect of component X". One row in
`points.md`:

```markdown
| ID | Reviewer quote (abridged) | Type | Severity | Effort | Strategy |
|---|---|---|---|---|---|
| R2.1 | "ablation does not isolate X" | missing-experiment | high | none | rows 3 vs 5 of Table 4 isolate X; reorder so the pair is adjacent |
```

The drafted response (OpenReview format here — one `## ` box, leads with the
answer, anchored, no padding):

```markdown
## Response to Reviewer 7Pqd (R2)

**[R2.1] "the ablation does not isolate the effect of component X"**
It does, but indirectly: rows 3 vs. 5 of Table 4 (Sec. 6.2, L412) differ
only in X. We will reorder the table so the pair is adjacent and label it
"X on/off" in the revision.
```

Verify before handing it over:

```
python3 skills/write-rebuttal/scripts/check_coverage.py points.md responses.md --strict
python3 skills/write-rebuttal/scripts/check_budget.py text responses.md --sections --venue venues/conferences/<id>.yml
```

Coverage passes because `R2.1` appears in a response and that section carries
anchors (`Table 4`, `Sec. 6.2`, `L412`); budget passes if the box is under
the venue's per-response limit. The same row drafts into `\rpoint{R2.1}{...}`
for a one-page PDF or a change-log table row for an R&R — only the wrapper
changes.

## Output

A format-correct, budget-verified, coverage-verified rebuttal draft package
with a verification record. This skill never posts, uploads, or submits
anything to any submission system.

## Guardrails

- Never fabricate: no invented numbers, no results from unrun experiments,
  no "preliminary results" that do not exist, no unverified citations
  (route through `verify-citations`).
- Never submit or post on the user's behalf; stop at files on disk.
- Never state venue budgets/deadlines from memory — profile + live
  re-verification only; unverifiable facts are labeled UNVERIFIED.
- Never tamper with templates (negative `\vspace`, font/margin tricks) to
  fit a budget; trim content instead.
- Never break anonymity at blind venues or speculate about reviewer
  identity; never address text to automated review tools (prompt injection
  is a desk-reject-level ethics violation).
- Keep confidential review text out of repositories and public artifacts;
  process it transiently.
