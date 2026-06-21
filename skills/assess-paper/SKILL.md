---
name: assess-paper
description: Gives the author one clear, friendly read on how good their paper is right now — its top strengths, its biggest risks, its scores, and exactly what to do next — by consolidating compliance, integrity, citation, conformance, and mock-review checks into a single Paper Health Report. Use when a researcher asks "how good is my paper", "is my paper ready", "what are the strengths and weaknesses of my paper", "give me an overall assessment", "review my whole paper", "what should I improve first", or "what's the state of my paper". Orchestrates preflight-check, verify-citations, check-originality, benchmark-paper, and simulate-reviewers, then summarizes the results in plain language with strengths first, a prioritized fix list, and an honest readiness read — never an acceptance prediction. Trigger words - how good is my paper, paper health, overall assessment, is it ready, strengths and weaknesses, what to improve, paper report, assess my paper.
---

# Assess Paper

The **one command that tells the author where they stand** — and explains *what's happening* so a non-expert isn't lost. It doesn't re-implement the checks; it runs the specialist skills and turns their output into a single, readable **Paper Health Report** that leads with strengths, then risks, then a ranked to-do list.

Built so the author understands their paper: strengths they should protect, problems ranked by how much they matter and how easily they're fixed, and a plain-language readiness read.

## When to use

- The author wants a single overview instead of running five skills and stitching the results together.
- Early ("how far off am I?") or late ("am I ready to submit?").
- A co-author/advisor wants a quick, honest state-of-the-paper.

## What it consolidates

| Dimension | Skill it runs | What it contributes to the report |
|---|---|---|
| Will it get desk-rejected? | [`preflight-check`](../preflight-check/SKILL.md) | compliance blockers (page limit, anonymization, missing sections) |
| Are the citations real? | [`verify-citations`](../verify-citations/SKILL.md) | fabricated/retracted/duplicate references |
| Is it original? | [`check-originality`](../check-originality/SKILL.md) | plagiarism / self-recycling overlap |
| Does it match strong work at the venue? | [`benchmark-paper`](../benchmark-paper/SKILL.md) | venue-fit scorecard + weakest dimensions |
| What will reviewers say? | [`simulate-reviewers`](../simulate-reviewers/SKILL.md) | strengths, weaknesses, rubric scores, decision-risk |

## Process

1. **Confirm the target** (venue + track) and read `.paper-memory/profile.yml` if present so the assessment matches the paper's positioning (a theory paper and an applied paper get judged differently).
2. **Run the checks** that apply to the draft's stage. Compliance and citations/originality are integrity gates; benchmark and mock-review are quality reads. Skip and say so if an input is missing (e.g. no `.bib` yet).
3. **Synthesize the Paper Health Report** (don't dump five raw outputs):
   - **Overall read** — one honest paragraph: roughly where this paper stands and the single most important thing to do next. Never an acceptance probability.
   - **Top strengths (lead with these)** — 3–5 concrete things the paper does well, drawn from the mock review and benchmark, each tied to a section. The author needs to know what to *protect* while editing.
   - **Biggest risks** — ranked by impact × ease of fix, each linking to the skill that fixes it.
   - **Scorecard + gates** — the venue-fit index, mock-review decision-risk band, and a clear pass/flag on the integrity gates (citations, originality, desk-reject).
   - **Do next** — a short ordered checklist.
4. **Write the report** to `paper-workspace/review/paper-health-report.md` in the user's paper workspace and present the summary in chat.

## Output

A single `paper-health-report.md`: overall read → strengths → ranked risks → scorecard & gates → do-next checklist. Each finding cites the underlying skill so the author can drill in. Plain language throughout — the goal is the author *understanding* their paper, not a wall of metrics.

## Guardrails

- **Strengths are mandatory and come first.** An assessment that is all problems is demoralizing and misleading — surface what genuinely works.
- Honest readiness read only — never a probability of acceptance or an award (see `benchmark-paper`, `simulate-reviewers`).
- Integrity gates (fabricated citations, plagiarism, desk-reject blockers) are reported as blockers, not averaged away by good scores elsewhere.
- It reports and explains; it never edits the paper or submits anything. Hand fixes to the specific skills.

## Memory

Uses the shared `.paper-memory/` convention (full spec: [`paper-memory-convention.md`](../paper-profile/references/paper-memory-convention.md)).

- **At start:** read `profile.yml` (positioning) and `lessons.md` (recurring weaknesses) so the report is personalized and tracks progress across drafts.
- **At end:** append a dated snapshot line — `date · assess-paper · venue-fit index, decision-risk, gates passed` — so improvement over time is visible; append any new recurring weakness.
- Create `.paper-memory/` on demand; local-only, never uploaded.
