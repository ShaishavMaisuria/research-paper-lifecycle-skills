# Verification signals — ground the VERIFY step in external checks

The single most important orchestration rule in this skill: **a stage is "done"
only when an external, measurable signal says so — never when the model judges
its own output complete.**

## Why self-reflection cannot be the completion signal

A model's self-reflection measures *plausibility and completeness*, not
*correctness*. A base model that hallucinated a fact will, with the same
parameters, "reflect" and confirm the hallucination — a positive feedback loop
that converges confidently on wrong output. Self-reflection improves general
reasoning but **degrades** on hallucination/grounding tasks. LLM-as-judge is
subjective, position-biased, and sycophantic. And calibration is worst exactly
when the model sounds surest — using a tool (fetching a CFP or a citation)
*induces* overconfidence, so the moment right after a lookup is when to be
**more** suspicious, not less.

Therefore every stage gate is anchored to a signal the model does not author.

## The signals this orchestrator uses (per stage)

| Stage | External signal | How it's produced |
|---|---|---|
| Lock requirements | The fetched fact matches the **primary source** | `parse-cfp` re-fetch; re-check the value on the live page, not the cache |
| Abstract | Word/char count ≤ the live venue bound | count vs the just-verified profile |
| Prose polish | Lint counts (hedge/passive/readability) **decrease** vs prior pass | `polish-prose/scripts/texprose.py` |
| Figures/tables | No undefined refs; captions present; floats placed | `polish-tables-figures/scripts/check_floats.py` |
| Citations | Every entry resolves to a real DOI/record; none retracted | `verify-citations/scripts/check_bibtex.py` (Crossref/DBLP) |
| Originality | Overlap below the integrity threshold | `check-originality` report |
| Compliance | Required sections present; page count ≤ limit; anonymized | `preflight-check/scripts/check_sections.py`, page check, anonymization linter |
| Compile | `latexmk` / build exits 0 | the build's own exit code |
| Checklist | Mandatory checklist macros/section present | grep for `\answerYes/No/NA` or the checklist heading |
| Q&A | Drill answers graded | `rehearse-qa/scripts/grade_answers.py` |

When a stage has such a signal, the gate is **the signal's pass/fail**, and
`reflect-and-improve`'s `score` subcommand records the before/after so "did it
improve" is a number with a KEEP / REVERT verdict, not a vibe.

## When there is no external oracle (judgment calls)

Some steps have no script that can be right or wrong — "is the contribution
framed well?", "is this reviewer concern load-bearing?". For these:

1. **Do not** let the model grade itself and call it verified. Say plainly that
   this step is a judgment with no measurable oracle.
2. **Escalate to the author** at the checkpoint — the author is the external
   judge. When assumptions or competing readings appear, stop and ask when an
   unverified assumption gates the next step, the request has more than one
   reading, or the model is confused.
3. Where a *partial* signal exists (e.g. a rubric in
   [`simulate-reviewers/references/rubrics.md`](../../simulate-reviewers/references/rubrics.md)),
   score against the rubric explicitly and show the scores, rather than emitting
   an unanchored "looks good."

## The independent-verifier pattern

Keep the **verifier role decoupled from the executor**. The skill that produced
the artifact is not the one that signs off on it: the producer runs, then a
separate check (a script, or `reflect-and-improve` with a rubric, or the author)
emits a structured verdict — status (`complete` / `partial` / `incomplete`),
what's missing, and a recommendation (`accept` / `retry` / `escalate`). On
`retry`, **replan only the low-scoring step**, preserving good prior results;
don't redo the whole stage. On `escalate`, hand it to the author. Concede, as
the underlying research does, that an automated verifier misses subtle factual
errors — so a non-trivial share of judgments should route to the human, by
design.

## Stop conditions (the loop must terminate)

Verification drives termination. Stop a stage's refine loop when **any** holds:

- the external signal passes (stage exit met);
- the metric's improvement between passes is below a small delta (diminishing
  returns) — keep the better version, stop polishing;
- a hard iteration cap (~3 passes) is reached → escalate;
- a token/time budget is exhausted → report and pause;
- the verifier recommends `escalate` → hand to the author.

Open-ended "keep improving" with no stop condition burns budget and over-edits
(drifting the author's voice). Always set the cap before starting the loop.
