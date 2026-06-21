---
name: verify-claims
description: Audit load-bearing paper claims against evidence in results, tables, figures, experiments, or citations. Use for claim audits, overclaiming checks, first or state-of-the-art claims, significant-result wording, prose-table number mismatches, and camera-ready or rebuttal evidence checks.
---

# Verify Claims

The claim-to-evidence gate. Reviewers attack the gap between what a paper
*asserts* and what it *shows* — an unbacked "we are the first", a
"state-of-the-art" with no comparison, a "significant improvement" with no
test, a speedup stated in the text that the table does not support. This skill
finds those candidate claims, makes the author map each to its evidence, and
produces a **claims matrix** (claim · location · evidence · status) so the gap
is visible and closeable before a reviewer finds it.

It is the *content* counterpart to [`verify-citations`](../verify-citations/SKILL.md):
that skill proves each reference in the `.bib` resolves to a real paper; this
skill proves each load-bearing sentence in the prose is backed by something in
*this* paper (a number, a figure, a table, an experiment) or a real citation.
Run both before any draft, rebuttal, or camera-ready leaves the machine.

## When to use

- The user asks to verify / audit / check **claims** (not citations): "are my
  claims supported?", "am I overclaiming?", "do my results match my tables?"
- Before a rebuttal — reviewers' top complaint is unsupported or overclaimed
  contributions; close the gaps first, or arm the rebuttal with the evidence.
- Before camera-ready or arXiv — last chance to soften an indefensible "first"
  or fix a number that drifted out of sync with a revised table.
- After `polish-tables-figures` regenerated a table, to confirm the prose still
  matches the new numbers.

## Inputs

- The paper's `.tex` (main file; the script follows `\input`/`\include`). Find
  it next to the `.bib`, or via the file with `\documentclass`.
- The author, in the loop: **the skill cannot decide whether a claim is true** —
  it surfaces candidates and the author supplies (or admits the absence of) the
  evidence. Copilot, not pilot.
- Optional: `.paper-memory/profile.yml` — `risk_appetite` and `contribution_type`
  set how hard the author wants to push novelty vs. hedge (see Memory).

## Process

1. **Extract candidate claims.** Deterministic work belongs to the script — do
   not eyeball the paper for claims:

   ```bash
   python3 scripts/claim_audit.py path/to/main.tex --json /tmp/claims.json
   ```

   It scans the prose (skipping math, comments, tables) for sentences carrying
   **novelty markers** ("first", "novel", "we are the only", "unlike prior
   work"), **superiority markers** ("outperforms", "state-of-the-art", "best",
   "superior"), **magnitude/result markers** ("significantly", "X% improvement",
   "Nx faster", "substantially"), and **generalization markers** ("always",
   "in all cases", "guarantees"). It also pulls every **numeric token in the
   prose** and every **numeric cell in the tables**, so you can cross-check.
   Each candidate gets a *type*, the sentence, and a `file:line` location.

   Useful variants:
   - `--type novelty` (or `superiority`, `result`, `generalization`) — focus one
     class of claim.
   - `--numbers` — emit only the prose-number vs. table-number cross-check list
     (for the "do my results match my tables?" question).
   - `--context N` — include N sentences of surrounding text per claim.
   - `--min-confidence high` — only the strongest-signal candidates (fewer false
     positives) when the paper is large.

   Exit codes: `0` no candidate claims found (rare — usually means the file
   parsed but is near-empty; check the input), `2` candidate claims were found
   (the normal case — they need author triage, not a "problem"), `1`
   operational failure (unreadable file, bad arguments). The script *finds*
   claims; it does not *judge* them — a nonzero `2` is the expected, healthy
   result, not a failure.

2. **Map each candidate to evidence — with the author.** This is the core of the
   skill and it is NOT automatable: the script flags "we achieve
   state-of-the-art accuracy"; only the author (or the paper's own Table 3) can
   say *which* result backs it. For each candidate, establish:
   - **Evidence** — the specific result, table/figure number, experiment,
     theorem, or citation that supports it (a `\ref`/`\label`, a table cell, a
     section). "Section 4" is not evidence; "Table 3, row BERT-large, +2.1 F1
     over the strongest baseline" is.
   - **Status** — `SUPPORTED` (evidence exists and matches), `WEAK`
     (evidence exists but is thinner than the claim — e.g. "significantly"
     with no significance test), `UNSUPPORTED` (no evidence found),
     `MISMATCH` (prose number disagrees with the table), or `SCOPED` (claim is
     fine once narrowed — see step 4).

   Read [references/claim-taxonomy.md](references/claim-taxonomy.md) for what
   each claim type requires as evidence and the standard reviewer attack on
   each.

3. **Apply the overclaiming rules.** Read
   [references/overclaiming-rules.md](references/overclaiming-rules.md). The
   high-frequency offenders:
   - **"first" / "novel"** needs a defensible scope and a literature check — an
     absolute "first to X" is a single-counterexample-away from a desk-level
     embarrassment. Prefer a scoped "first to X *under constraint Y*".
   - **"state-of-the-art" / "outperforms"** needs the comparison: which
     baselines, on which benchmark, by how much, and whether the baselines are
     current and fairly tuned.
   - **"significantly" / "substantial"** is a statistical word: it needs a test
     (and the test named), not just a bigger mean. If no test was run, the word
     should change, not the data.
   - **Numbers in prose** must equal the numbers in the tables/figures they
     summarize. The script's `--numbers` mode lists prose vs. table numerics;
     reconcile every mismatch (a revised table that left a stale sentence behind
     is the classic camera-ready bug).

4. **Decide the fix per claim, with the author.** Three honest moves, never a
   fourth:
   - **Back it** — add/point to the missing evidence (a result already in the
     paper, a citation, an experiment to run).
   - **Scope it** — narrow the claim to what the evidence actually supports
     ("first" → "first *under Y*"; "always" → "in our experiments").
   - **Cut it** — remove the claim if it cannot be backed or scoped.
   Never the fourth move: inventing evidence, a result, a citation, or a
   significance test that was not run. An honest "this
   claim is unsupported" beats a fabricated backing.

5. **Write the claims matrix** to
   `paper-workspace/review/claims-matrix.md`: one row per
   load-bearing claim — *claim · location · type · evidence · status · suggested
   fix*. Lead the chat summary with counts by status and the most dangerous
   open items (UNSUPPORTED and MISMATCH first). Append the run to `INDEX.md`.

6. **Re-run after fixes.** Once the author edits, re-run `claim_audit.py` (and
   `--numbers`) to confirm softened/scoped claims no longer trip the markers and
   no prose/table mismatch remains. Stop when every load-bearing claim is
   SUPPORTED, SCOPED, or an explicitly author-accepted WEAK — not on an
   open-ended "keep improving" loop (cap at a couple of passes; report what
   remains open).

## Output

- `claim_audit.py` stdout (and `--json`): candidate claims with type, location,
  and the prose-vs-table numeric cross-check — a worklist, not a verdict.
- `paper-workspace/review/claims-matrix.md`: the reviewable claims matrix the
  author fills in and acts on, plus a one-line `INDEX.md` entry.
- A chat summary: counts by status, the riskiest open claims, and the
  per-claim fix (back / scope / cut) — never a fabricated backing.

## Hard rules

- **The skill never decides a claim is true or false on its own.** It has no
  oracle for "is this the first paper to do X" or "is this really
  state-of-the-art" — it surfaces the candidate and routes the judgment to the
  author and the paper's own evidence. Do not use the model's self-assessment as
  the verification signal (it measures plausibility, not correctness, and is
  worst exactly when most confident).
- **Never fabricate evidence.** No invented result, table number, citation,
  baseline, or significance test to "support" a claim. If it cannot be backed,
  it must be scoped or cut.
- **Numbers are facts, not prose.** A prose number that disagrees with its table
  is a MISMATCH to reconcile from the *table* (or the underlying result), never
  by editing the table to match a sentence the author likes better.
- **"first"/"SOTA"/"significant" are load-bearing words with evidentiary cost.**
  Treat them as claims requiring proof, not rhetorical flourish.
- This skill checks claim→evidence *within this paper*; it does not verify the
  `.bib` resolves — that is [`verify-citations`](../verify-citations/SKILL.md).
  When a claim's evidence is a citation, hand that reference to verify-citations.
- It reports and explains; it never edits the paper or submits anything. The
  author makes every back/scope/cut decision.

## Adapt to your discipline

Defaults target CS venues (IEEE/ACM/ML). The marker lexicons and evidence
expectations are field-specific: a theory paper's claims trace to theorems and
proofs (not tables); an HCI paper's to study design and significance reporting;
a survey's to coverage and taxonomy completeness rather than "outperforms".
Edit `references/claim-taxonomy.md` and the marker lists in `claim_audit.py`
(documented inline) for your field's claim vocabulary and standards of proof.

## Bundled resources

- `scripts/claim_audit.py` — extracts candidate claim sentences and the
  prose/table numeric cross-check from a `.tex`. Stdlib only; `--help` for all
  options. Run it; do not hand-scan the paper.
- [references/claim-taxonomy.md](references/claim-taxonomy.md) — the claim types,
  what evidence each needs, and the standard reviewer attack on each.
- [references/overclaiming-rules.md](references/overclaiming-rules.md) — the
  high-frequency overclaims ("first", "SOTA", "significant", stale numbers) and
  the back/scope/cut remedy for each.

## Memory

Uses the shared `.paper-memory/` convention (full spec:
[`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `lessons.md` to skip re-flagging claims the author already
  scoped or backed this cycle, and lead with any `recurring` overclaiming habit
  (e.g. "tends to write absolute 'first' claims; scope them up front"). Read
  `profile.yml` `risk_appetite` — `conservative` authors want every WEAK claim
  hedged; `aggressive` authors accept defensible WEAK claims they will fight for
  in review.
- **At end:** append durable findings via
  `reflect-and-improve`'s `reflect_log.py append` in the shared format
  `- [YYYY-MM-DD] (verify-claims | <scope>) issue -> recommendation`. A habit
  across the paper or across papers (e.g. unscoped novelty claims, "significant"
  without a test) is `recurring`; a single fixed sentence is `this-paper`. Never
  record a fabricated backing — only the pattern and the honest fix.
- Create `.paper-memory/` on demand if absent and offer to add it to the
  project `.gitignore`. Local-only; never uploaded or copied into this repo.
