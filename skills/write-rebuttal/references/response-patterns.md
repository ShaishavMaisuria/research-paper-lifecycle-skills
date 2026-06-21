# Response patterns, evidence anchoring, and tone

Shared strategy for all three rebuttal formats. Format-specific mechanics
live in the sibling files (`cvpr-one-page.md`, `openreview-threads.md`,
`revise-and-resubmit.md`).

## Contents

- [The evidence-anchoring rule](#the-evidence-anchoring-rule)
- [The triage matrix and point-ID convention](#the-triage-matrix-and-point-id-convention)
- [Criticism taxonomy and the response pattern for each](#criticism-taxonomy-and-the-response-pattern-for-each)
- [Tone rules](#tone-rules)
- [Conceding well](#conceding-well)
- [What never goes in a rebuttal](#what-never-goes-in-a-rebuttal)

## The evidence-anchoring rule

Every sentence in a rebuttal that makes a claim must point at evidence the
reviewer can check, in this priority order:

1. **The submitted PDF**: `Sec. 4.2`, `Table 3`, `Fig. 2 (right)`,
   `Eq. (5)`, `Appendix C`, `L231` or `lines 96–104` (line numbers exist in
   review-mode templates — use them, they are the cheapest anchor).
2. **The submitted supplementary material** (if the venue lets reviewers see
   it): `Supp. Sec. B`, `video at 0:42`.
3. **A published, verifiable source**: `[17]`, with the claim located
   precisely ("their Sec. 7 leaves the streaming case open"). Any NEW
   citation introduced in a rebuttal must first go through the
   `verify-citations` skill — a hallucinated reference in a rebuttal is
   fatal to credibility and unfixable after posting.
4. **A new result produced during the rebuttal window** — only if the venue
   permits new experiments in rebuttals (many ban them; CVPR-style rules
   ban new contributions/experiments unless reviewers specifically
   requested them). Label it as new: "In response to R2.1 we ran X: ...".

If no evidence exists for a claim, do not assert it. The honest moves are:
commit to a concrete revision ("we will add the dense-case bound to
Sec. 4.3"), scope the claim down, or concede the point. A response with no
anchor reads as assertion — `scripts/check_coverage.py` flags such
sections.

Anchor formats the checker recognizes: `Sec. 4` / `Section 4.2`, `Table 3`,
`Fig. 2` / `Figure 2`, `Eq. (5)`, `Appendix B`, `line 120` / `lines 96–104`,
`L231`, `[17]`, "abstract".

## The triage matrix and point-ID convention

Drafting starts from a triage matrix (the `triage-reviews` skill produces
one; build it inline if that skill is unavailable). Point IDs:

- `R<k>.<n>` — point `n` of reviewer `k` (e.g. `R2.3`)
- `AC.<n>` — area chair / meta-reviewer point
- `MR.<n>` — separate meta-review, where venues distinguish it

Matrix columns:

| ID | Reviewer quote (abridged) | Type | Severity | Effort | Strategy |
|---|---|---|---|---|---|
| R1.1 | "no comparison against B" | missing-baseline | high | medium | point to Table 2 + add row |

- **Type**: one of the taxonomy categories below.
- **Severity**: high (drives the score) / medium / low (polish).
- **Effort**: what answering costs — none (already in paper), low (text
  edit), medium (re-run/re-plot), high (new experiment).
- **Strategy**: one clause; becomes the topic sentence of the response.

Order of attention: high-severity/low-effort first (cheap score movers),
then high/medium, then everything else. Every ID must appear in the final
response — `check_coverage.py` enforces this. Low-severity points may share
one grouped response ("Typos and clarity: R1.4, R3.2 — all fixed").

## Criticism taxonomy and the response pattern for each

**Misreading / misunderstanding.** The reviewer missed something that is in
the paper. Never say "the reviewer misunderstood". Pattern: agree the text
made the misreading possible, point at the evidence, promise the clarity
fix. *"This is stated at L231, but we agree it is easy to miss — we will
repeat the assumption where it is used (Sec. 4.3)."*

**Missing experiment / baseline.** (a) If it exists under another name:
point at it and rename/relabel. (b) If it can be run in the window and the
venue allows new results: run it, report numbers plainly, label as new.
(c) If it cannot be run or is disallowed: explain why the existing evidence
already answers the underlying question, or commit to it for the revision.
Never report numbers for an experiment that was not actually run.

**Novelty challenge ("similar to [17]").** Two-part pattern: (1) the
*problem* delta — what setting/assumption differs, anchored to your Sec. 2
and their paper's own scoping statements; (2) the *technique* delta — which
mechanism is new. Concede genuine overlap explicitly; partial concession
plus a precise delta is far more credible than total denial.

**Significance / scope ("too narrow", "who needs this").** Anchor to
external, checkable signals: the application in the intro, the dataset's
provenance, citation of the problem by others. Do not inflate. If the venue
has a better-fitting track, that argument belongs to the AC, made neutrally.

**Clarity / presentation.** Cheapest wins available. Accept, enumerate the
exact edits ("we will: (1) rename X→Y throughout; (2) move Fig. 3 next to
its discussion"), and bound them ("presentation-level, within the page
budget"). Never argue a clarity point.

**Correctness concern.** Highest stakes — answer first and with the most
care. If the reviewer is wrong, walk the chain step by step with anchors to
each equation/lemma. If the reviewer is right, say so immediately, state
the blast radius precisely (which claims survive), and what the fix is.
Hiding a real flaw that the AC then confirms ends the paper.

**Related-work gap.** Verify the suggested reference exists and says what
the reviewer claims (route through `verify-citations`). If relevant: "We
will cite [X] and contrast in Sec. 2 (one paragraph): ...delta...". If the
suggested work is the reviewer's own and marginal, cite it if defensible,
neutrally; never speculate about reviewer identity either way.

**Score-without-substance ("not exciting", score with empty text).** Do not
attack the review. Restate the contribution in two sentences with the
strongest anchors, answer whatever fragment of substance exists, and let
the AC see the asymmetry. In OpenReview formats, a polite closing ask is
acceptable: "we hope the clarifications above address the concerns and
would appreciate the reviewer reconsidering the assessment."

## Tone rules

- Open by thanking reviewers once, briefly. No groveling, no flattery arcs.
- Refer to reviewers as R1/R2/R3 (or their OpenReview codes); never "the
  reviewer is wrong/confused"; criticize text, not people.
- Lead every response with the answer, not the apology: "Table 2 already
  contains this comparison" beats three sentences of preamble.
- "We agree" and "Good point" are full sentences — use them and move on.
- Never sarcastic, never defensive, never counting wrongs. Assume the AC is
  the real audience and is reading 20 of these.
- Match the venue register: rebuttals are argued; R&R response letters are
  collaborative ("we have done X" rather than "we would do X").

## Conceding well

A rebuttal that concedes nothing is not believed. Pick the points where the
reviewer is simply right — typically 1–3 clarity or scoping points — and
concede them cleanly with the fix. This buys credibility for the points you
contest. The concede/contest ratio is a strategy decision: make it
explicitly when building the matrix, not mid-sentence while drafting.

## What never goes in a rebuttal

- Fabricated or extrapolated numbers; results of experiments not actually
  run; "preliminary results suggest" for runs that do not exist.
- New citations that have not been verified via `verify-citations`.
- Identity leaks: author names, grant numbers, "in our previous work [x]"
  phrased in first person, links to identifiable repos or project pages.
- External links in general, where the format bans them (CVPR-style bans
  links; NeurIPS-style allows none except anonymized code to ACs — check
  the profile and live instructions).
- Speculation about reviewer identity, expertise, or motives.
- Text addressed to automated tools, hidden text, white-on-white content,
  or any prompt-injection — venues now treat this as an ethics violation
  and desk-reject grounds.
- Promises that cannot be kept within the venue's revision allowance
  (e.g. "we will add 4 pages of analysis" when camera-ready allows +1 page).
