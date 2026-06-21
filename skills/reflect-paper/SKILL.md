---
name: reflect-paper
description: >-
  Runs a two-pass paper reflection loop with a Researcher pass and a Writer
  pass. Use when the user asks to reflect on a paper, improve a draft, run a
  research-agent and writer-agent review, critique the paper before submission,
  find both technical and writing issues, or produce a revision plan. The
  Researcher pass checks claims, citations, evidence, venue fit, missing
  related work, and reviewer risk; the Writer pass checks framing, structure,
  abstract, related work, prose, tables/figures, and response clarity. Outputs
  a merged action plan with evidence, priority, owner, and next skill to run.
---

# Reflect Paper

Run a structured reflection loop over a research-paper draft. Treat this as two
separate perspectives, then merge them into one revision plan:

- **Researcher pass** — technical truth, evidence, citations, venue fit,
  novelty, limitations, reviewer risk.
- **Writer pass** — narrative, framing, section structure, abstract, related
  work placement, prose, figures/tables, reader flow.

This is an orchestration skill: it calls on sibling skills when their narrower
checks are needed, but it owns the reflection protocol and final synthesis.

If the runtime supports delegated agents or subagents, split the reflection
into two independent workers:

1. Send a Researcher worker the draft, target venue/context, and the Researcher
   pass checklist only.
2. Send a Writer worker the draft, target venue/context, and the Writer pass
   checklist only.
3. Merge both outputs yourself; do not let either worker decide the final
   verdict alone.

If delegation is unavailable, run the same passes sequentially. Keep separate
notes for each pass so technical-risk findings do not flatten writing feedback,
and writing polish does not hide correctness concerns.

## When to use

- "Reflect on this paper before I submit"
- "Run a research agent and writer agent on my draft"
- "Critique this draft from both technical and writing angles"
- "Give me a revision plan"
- "What should I fix before sending this to my advisor / reviewers?"
- "Do a final paper reflection pass"

## Inputs

- The draft: LaTeX source, PDF, markdown, Word-exported text, or pasted
  sections.
- Optional: target venue or CFP URL.
- Optional: bibliography file, related-work notes, reviews, or advisor
  feedback.
- Optional: the user's current goal, such as submission readiness, camera-ready
  polish, rebuttal, or presentation prep.

## Process

### 1. Scope The Reflection

Identify the lifecycle stage and what "good" means for this pass:

| Stage | Primary concern |
|---|---|
| Early draft | Missing contribution, weak framing, incomplete evidence. |
| Pre-submission | Venue fit, page budget, anonymization, citation reliability, reviewer risk. |
| Rebuttal | Review coverage, evidence anchors, tone, response budget. |
| Camera-ready | Required final-file steps, de-anonymization, acknowledgments, source consistency. |
| Presentation | Talk story, timing, Q&A risk, slide/poster readability. |

If a venue or CFP is involved, use `parse-cfp` or `add-venue-profile` before
relying on page limits, blind level, required sections, or deadlines.

### 2. Researcher Pass

Read for correctness and evidence. Check:

- Core claim: what the paper says it contributes, and whether the evidence
  actually supports it.
- Novelty and related work: missing comparisons, closest competitors, thin or
  overstated deltas.
- Citations: unresolved entries, suspicious metadata, fabricated-looking
  references, uncited claims.
- Methods and evaluation: assumptions, baselines, ablations, datasets,
  reproducibility, statistics, limitations.
- Venue fit: track expectations, page budget, anonymity, required sections,
  LLM/AI-use policy, artifact expectations.
- Reviewer risk: likely objections and what evidence would defuse them.

Delegate as needed:

| Need | Use |
|---|---|
| Find missing related work | `find-papers`, `literature-review` |
| Fetch legal OA copies | `fetch-paper` |
| Check bibliography | `verify-citations` |
| Study venue exemplars | `study-exemplars` |
| Simulate reviewer risk | `simulate-reviewers` |
| Check CFP/venue facts | `parse-cfp`, `select-venue`, `tailor-to-venue` |

Record findings as: `finding`, `evidence`, `risk`, `suggested fix`, and
`confidence`.

### 3. Writer Pass

Read for communication and persuasion. Check:

- One-sentence paper promise: can a reader say what the paper does and why it
  matters?
- Abstract: motivation, gap, approach, result, impact, and venue-specific
  length/keyword rules.
- Introduction: problem setup, contribution bullets, reader contract.
- Related work: clustered themes and explicit deltas, not a laundry list.
- Method and evaluation: section order, figure/table references, claim titles,
  readable transitions.
- Prose: overclaiming, hedging, AI-sounding filler, terminology drift,
  passive contribution statements.
- Figures and tables: captions, crossrefs, color accessibility, layout, and
  whether each visual answers a reader question.

Delegate as needed:

| Need | Use |
|---|---|
| Abstract rewrite or lint | `write-abstract` |
| Related work drafting | `draft-related-work` |
| Full review synthesis | `literature-review` |
| Prose polish | `polish-prose` |
| Tables and figures | `polish-tables-figures` |
| Talk/poster translation | `make-slides`, `write-talk-script`, `make-poster` |

Record findings as: `reader problem`, `location`, `revision`, `expected
benefit`, and `next skill`.

### 4. Reflection Merge

Merge the two passes into a prioritized plan. Do not average away conflicts:
when the Researcher pass wants more caveats and the Writer pass wants a
sharper claim, state the tradeoff and propose a wording that is both accurate
and readable.

Use this priority scale:

| Priority | Meaning |
|---|---|
| P0 | Blocks submission or creates serious correctness/integrity risk. |
| P1 | Likely affects review outcome or reader understanding. |
| P2 | Improves clarity, polish, or confidence. |
| P3 | Nice-to-have cleanup. |

### 5. Output

Return a concise reflection report:

1. **Verdict** — ready / close / needs major revision / not ready.
2. **Researcher pass** — top technical, evidence, citation, and venue risks.
3. **Writer pass** — top framing, structure, prose, and visual risks.
4. **Merged action plan** — prioritized table with owner/pass, location,
   action, next skill, and estimated effort.
5. **Open questions** — facts that require user input or live verification.

## Guardrails

- Never invent papers, results, deadlines, page limits, or venue rules.
- Do not modify technical claims to sound stronger unless the evidence supports
  them.
- Keep confidential reviews and unpublished paper content local.
- For legal/copyright safety, fetch papers only from legal open-access sources
  and do not reproduce abstracts or paper text in the report.
